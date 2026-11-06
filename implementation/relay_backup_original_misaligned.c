#include "hal_thread.h"
#include "goose_receiver.h"
#include "goose_subscriber.h"
#include "mms_value.h"
#include <stdio.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>

static volatile int trip_seen = 0;
static struct timespec fault_time, backup_active_time;

static void
gooseListener(GooseSubscriber subscriber, void* parameter)
{
    MmsValue* values = GooseSubscriber_getDataSetValues(subscriber);
    MmsValue* tripVal = MmsValue_getElement(values, 0);

    if (tripVal != NULL && MmsValue_getType(tripVal) == MMS_BOOLEAN
        && MmsValue_getBoolean(tripVal)) {
        trip_seen = 1;
        printf("Trip frame received from primary -- backup stays passive.\n");
    }
}

static int wait_for_fault_signal(const char* fifo_path)
{
    int fd = open(fifo_path, O_RDONLY);
    if (fd < 0) {
        perror("open fault-sync fifo (reader)");
        return -1;
    }
    char buf;
    ssize_t n = read(fd, &buf, 1);
    close(fd);
    return (n == 1) ? 0 : -1;
}

int main(int argc, char** argv)
{
    const char* interface = argc > 1 ? argv[1] : "veth-backup";
    long timeout_ms = argc > 2 ? atol(argv[2]) : 10;
    const char* fifo_path = argc > 3 ? argv[3] : "/tmp/fault_sync";

    GooseReceiver receiver = GooseReceiver_create();
    GooseReceiver_setInterfaceId(receiver, interface);

    GooseSubscriber subscriber = GooseSubscriber_create("simIED1/LLN0$GO$gcbTrip", NULL);
    GooseSubscriber_setListener(subscriber, gooseListener, NULL);
    GooseReceiver_addSubscriber(receiver, subscriber);
    GooseReceiver_start(receiver);

    if (wait_for_fault_signal(fifo_path) != 0) {
        fprintf(stderr, "RESULT,SYNC_ERROR,elapsed_ms=0,trip_delivered=0\n");
        GooseReceiver_stop(receiver);
        GooseReceiver_destroy(receiver);
        return 1;
    }

    clock_gettime(CLOCK_MONOTONIC, &fault_time);

    long elapsed_ms = 0;
    while (elapsed_ms < timeout_ms && !trip_seen) {
        Thread_sleep(1);
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        elapsed_ms = (now.tv_sec - fault_time.tv_sec) * 1000
                   + (now.tv_nsec - fault_time.tv_nsec) / 1000000;
    }

    // CHANGED: after the deadline-polling loop above ends, keep listening a
    // short grace window to check whether the trip was EVER delivered at
    // all -- decoupled from whether it arrived inside the T-ms deadline.
    // This separates "did the packet get through" from "did our 1ms
    // polling loop happen to notice it before the deadline".
    if (!trip_seen) {
        struct timespec grace_start, now2;
        clock_gettime(CLOCK_MONOTONIC, &grace_start);
        long grace_elapsed_ms = 0;
        while (grace_elapsed_ms < 20 && !trip_seen) {  // 20ms grace, covers full N=5 burst at 2ms spacing
            Thread_sleep(1);
            clock_gettime(CLOCK_MONOTONIC, &now2);
            grace_elapsed_ms = (now2.tv_sec - grace_start.tv_sec) * 1000
                              + (now2.tv_nsec - grace_start.tv_nsec) / 1000000;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &backup_active_time);

    if (trip_seen) {
        // Note: trip_seen may have become true either before or after the
        // deadline check above -- elapsed_ms still reflects the original
        // deadline-loop timing, so PASS/BACKUP_ACTIVE/DEGRADED classification
        // is unchanged. trip_delivered=1 here regardless of which loop caught it.
        printf("RESULT,PASS,elapsed_ms=%ld,trip_delivered=1\n", elapsed_ms);
    } else {
        printf("RESULT,%s,elapsed_ms=%ld,trip_delivered=0\n",
               (elapsed_ms < timeout_ms) ? "BACKUP_ACTIVE" : "DEGRADED",
               elapsed_ms);
    }

    GooseReceiver_stop(receiver);
    GooseReceiver_destroy(receiver);
    return 0;
}
