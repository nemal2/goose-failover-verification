\
# Makefile for the Track A relay binaries.
# Assumes this file sits in ~/track-a/relay/, as a sibling of ~/track-a/libiec61850/.
LIBIEC_HOME = ../libiec61850

INCLUDES = -I$(LIBIEC_HOME)/config
INCLUDES += -I$(LIBIEC_HOME)/hal/inc
INCLUDES += -I$(LIBIEC_HOME)/src/common/inc
INCLUDES += -I$(LIBIEC_HOME)/src/mms/inc
INCLUDES += -I$(LIBIEC_HOME)/src/mms/inc_private
INCLUDES += -I$(LIBIEC_HOME)/src/mms/asn1
INCLUDES += -I$(LIBIEC_HOME)/src/iec61850/inc
INCLUDES += -I$(LIBIEC_HOME)/src/iec61850/inc_private
INCLUDES += -I$(LIBIEC_HOME)/src/goose
INCLUDES += -I$(LIBIEC_HOME)/src/sampled_values
INCLUDES += -I$(LIBIEC_HOME)/src/logging
INCLUDES += -I$(LIBIEC_HOME)/src/tls
INCLUDES += -I$(LIBIEC_HOME)/src/r_session

LIB = $(LIBIEC_HOME)/build/libiec61850.a
CFLAGS = -g
LDLIBS = -lpthread

all: relay_primary relay_backup

relay_primary: relay_primary.c $(LIB)
	$(CC) $(CFLAGS) -o relay_primary relay_primary.c $(INCLUDES) $(LIB) $(LDLIBS)

relay_backup: relay_backup.c $(LIB)
	$(CC) $(CFLAGS) -o relay_backup relay_backup.c $(INCLUDES) $(LIB) $(LDLIBS)

clean:
	rm -f relay_primary relay_backup
