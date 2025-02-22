
### import

from critbot import crit_defaults
import critbot.plugins.syslog
import logging
import re
import sys

### config

config = dict(

    ### workers

    host='127.0.0.1',                                   # Identifies a worker in "workers" list, so should be set to LAN IP address (not 0.0.0.0) in config/local.py
    listen_any=False,                                   # May be enabled on firewall-protected host to listen on any network interface (0.0.0.0).
    port_for_workers=24000,                             # May be changed with argv[1]
    port_for_clients=25000,                             # May be changed with argv[2]

    workers=[                                           # Should be set in config/local.py or config/mqks_workers.py
        '127.0.0.1:24000:25000',
        '127.0.0.1:24001:25001',
    ],

    ### log

    environment='PROD',                                 # To see where CRIT-s are from.
    logger_name='mqks.server',
    logger_level=logging.INFO,
    grep='',                                            # Log requests and responses with this substring in INFO mode to avoid too spammy and slow full DEBUG. See usage in "stats.py".
    get_extra_log_plugins=lambda: [],                   # E.g. lambda: [critbot.plugins.slack.plugin(...)]

    ### top_events

    top_events=False,                                   # Enable to collect stats how often each event_mask was published.
    top_events_seconds=60*5,                            # Report and reset stats each N seconds.
    top_events_limit=50,                                # Top-N events to report.
    top_events_id=re.compile(r'[0-9a-f]{24,}|[0-9]+'),  # 24+ hex or any decimal IDs will be masked as "{id}".

    ### gbn_profile

    gbn_profile=False,                                  # Eval "gbn_profile.enable(),get(),disable()" from any worker to manage gbn profiler all workers.
    gbn_seconds=60*5,                                   # Report and reset profile each N seconds.

    ### other

    backlog=256,                                        # How many clients and other workers may wait for accept by TCP server.
    unix_sock_dir='/tmp/mqks',                          # Directory to connect workers on the same host via UNIX sockets.
    warn_command_bytes=100*1024,                        # Warn if command sent between workers is that big - may point to client-side problem.
    block_seconds=1,                                    # Wait at most N seconds before checking some condition again. Less seconds = more reactive = more CPU load.
    rebind_confirm_seconds=0.1,                         # Time for other workers to get rebind. "--confirm" is used mainly in tests.
    id_length=24,                                       # Length of random ID. More bytes = more secure = more slow.
    client_postfix_length=4,                            # Length of random part of client ID. More bytes = more secure = more slow.
    remove_mask_cache_limit=100500,                     # How many compiled regexps for "--remove-mask" feature are cached before cache is cleared.
    seconds_before_gc=60,                               # Trying to minimize memory leaks by forcing GC from time to time.
)

# configure mqks workers

from mqks.server.config.mqks_workers import mqks_workers_map

mqks_servers = mqks_workers_map.keys()
if len(sys.argv) > 3:
    servers_arg = ''
    for i, arg in enumerate(sys.argv[3:]):
        i += 3
        if arg.startswith('--mqks-servers='):
            servers_arg = arg.split('=')[1]
            break
        elif arg == '--mqks-servers' and len(sys.argv) > i + 1:
            servers_arg = sys.argv[i + 1]
            break

    if servers_arg:
        mqks_servers = list(set([s.strip() for s in servers_arg.split(',')]))

mqks_workers = []
for s in mqks_servers:
    mqks_workers += mqks_workers_map[s]

config['workers'] = mqks_workers

### crit, log

def init_log():
    import socket
    log = logging.getLogger(config['logger_name'])
    try:
        syslog_plugin = critbot.plugins.syslog.plugin(logger_name=config['logger_name'], logger_level=config['logger_level'])
        syslog_plugin.handler.setFormatter(logging.Formatter('.%(msecs)03d %(message)s'))

        crit_defaults.subject = '{environment} {logger_name}@{host} CRIT'.format(**config)
        crit_defaults.plugins = [syslog_plugin] + config['get_extra_log_plugins']()
        crit_defaults.crit_in_crit = log.critical
        crit_defaults.stop_spam_file.enabled = True
    except socket.error as e:
        log.critical('Exception: %s', e)