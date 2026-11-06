#include "goose_publisher.h"
#include "hal_thread.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>

// CHANGED: was 20 -- capped at N to match the formal model's attempt bound
// (Part 5 Relay template). If you'd rather keep the fuller 20-frame burst
// and document the N-vs-burst-count gap as a discussion point per Part 7.3
// instead, just change this back and note it in your methods section.
#define TRIP_ATTEMPTS 5
#define RETRY_INTERVAL_MS 2 // matches the model's r >= 2 retry spacing

// CHANGED: signal the backup the instant the fault actually starts, instead
// of relying on the two processes' launch times to line up.
static int signal_fault(const char* fifo_path)
{
    int fd = open(fifo_path, O_WRONLY);
    if (fd < 0) {
        perror("open fault-sync fifo (writer)");
        return -1;
    }
    char buf = 1;
    ssize_t n = write(fd, &buf, 1);
    close(fd);
    return (n == 1) ? 0 : -1;
}

int main(int argc, char** argv)
{
    const char* interface = argc > 1 ? argv[1] : "veth-primary";
    const char* fifo_path = argc > 2 ? argv[2] : "/tmp/fault_sync";

    CommParameters gooseCommParameters = {0};
    gooseCommParameters.appId = 1000;
    memcpy(gooseCommParameters.dstAddress, (uint8_t[]){0x01,0x0c,0xcd,0x01,0x00,0x01}, 6);

    GoosePublisher publisher = GoosePublisher_create(&gooseCommParameters, interface);
    GoosePublisher_setGoCbRef(publisher, "simIED1/LLN0$GO$gcbTrip");
    GoosePublisher_setConfRev(publisher, 1);
    GoosePublisher_setTimeAllowedToLive(publisher, 500);
    GoosePublisher_setGoID(publisher, "gcbTrip");
    GoosePublisher_setDataSetRef(publisher, "simIED1/LLN0$AnalogValues");

    LinkedList dataSetValues = LinkedList_create();
    LinkedList_add(dataSetValues, MmsValue_newBoolean(false)); // steady state: no trip

    // Steady-state heartbeat: slow retransmission, no trip.
    // Backup no longer times its deadline off process launch, so this
    // duration doesn't affect measurement accuracy -- only the fault-sync
    // signal below does.
    for (int i = 0; i < 2; i++) {
        GoosePublisher_publish(publisher, dataSetValues);
        Thread_sleep(200); // 1s heartbeat
    }

    // --- Fault event: switch payload to "trip" and burst-retransmit ---
    // FIXED: LinkedList_get() returns the list-node wrapper, not the stored
    // MmsValue itself -- LinkedList_getData() unwraps it. Casting the
    // wrapper straight to MmsValue* (as the book's own listing does) corrupts
    // the value and segfaults a few calls later inside the GOOSE encoder.
    MmsValue_setBoolean((MmsValue*) LinkedList_getData(LinkedList_get(dataSetValues, 0)), true);

    // Tell the backup the fault has started, THEN start sending. This is
    // the reference point relay_backup.c uses as its own t=0.
    if (signal_fault(fifo_path) != 0) {
        fprintf(stderr, "RESULT,SYNC_ERROR,elapsed_ms=0\n");
        GoosePublisher_destroy(publisher);
        return 1;
    }

    struct timespec first_trip_time;
    clock_gettime(CLOCK_MONOTONIC, &first_trip_time);
    printf("FIRST_TRIP_PUBLISHED,sec=%ld,nsec=%ld\n",
           first_trip_time.tv_sec, first_trip_time.tv_nsec);

    for (int i = 0; i < TRIP_ATTEMPTS; i++) {
        GoosePublisher_publish(publisher, dataSetValues);
        Thread_sleep(RETRY_INTERVAL_MS); // fast burst retransmission
    }

    GoosePublisher_destroy(publisher);
    return 0;
}

