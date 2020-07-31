import psutil
from datetime import datetime
import pandas as pd
import time
import os
import argparse
import time
import logging
import sys
import signal

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger(__name__)
should_continue = True


def get_process_with_name(name):
    found = None
    for pr in psutil.process_iter():
        with pr.oneshot():
            pid = pr.pid
            if pid == 0:
                continue
            if pr.name().find(name) >= 0:
                logger.info("Found one process: {}".format(pr.name()))
                if found is None:
                    found = pr

    return found


def get_memory_usage(pr):
    try:
        # get the memory usage in bytes
        memory_usage = pr.memory_full_info().uss
    except psutil.AccessDenied:
        memory_usage = 0
    return memory_usage


def get_cpu_usage(pr):
    cpu_usage = pr.cpu_percent()
    return cpu_usage


def get_number_threads(pr):
    return pr.num_threads()


def config_argument_parser():
    parser = argparse.ArgumentParser(description='Tool to monitor a process')
    parser.add_argument('--process', help='process to monitor')
    parser.add_argument('--report_path', help='path to keep report')
    parser.add_argument('--report_name', help='name of the report', default="report.csv")
    parser.add_argument('--collect_interval', help='collect interval in millisecond', default=1000, type=int)
    parser.add_argument('--headless', default=False, type=bool)
    return parser.parse_args()


def get_time():
    timestamp = time.time()
    return datetime.fromtimestamp(timestamp)

def format_memory(bytes):
    return bytes / 1024 / 1024


def signal_handler(sig, frame):
    print(sig, frame)
    logger.info("SIGINT received")
    global should_continue
    should_continue = False


def report(table, report_name, path=None):
    if path is None:
        path = os.path.dirname(os.path.realpath(__file__))
    df = pd.DataFrame(table)
    df.set_index('time', inplace=True)
    df.sort_values('time', inplace=True, ascending=True)
    logger.info("CPU Usage(max: {},min: {},average: {},median: {})".format(df["cpu_usage"].max(), df["cpu_usage"].min(), df["cpu_usage"].mean(), df["cpu_usage"].median()))
    logger.info("Memory Usage(max: {},min: {},average: {},median: {})".format(df["memory_usage"].max(), df["memory_usage"].min(), df["memory_usage"].mean(), df["memory_usage"].median()))
    if sys.platform.startswith("win"):
        df.to_csv("{}\\{}".format(path, report_name), index=True)
    if sys.platform.startswith("linux"):
        df.to_csv("{}//{}".format(path, report_name), index=True)
    pass


if __name__ == '__main__':
    args = config_argument_parser()
    logger.propagate = not args.headless
    pr = get_process_with_name(args.process)
    if pr is None:
        logger.warning("Cannot find any process includes {}".format(args.process))
        sys.exit(0)
    try:
        table = []
        signal.signal(signal.SIGINT, signal_handler)
        name = pr.name()
        while should_continue:
            timestamp = get_time()
            memory_usage = format_memory(get_memory_usage(pr))
            cpu_usage = get_cpu_usage(pr)
            threads = get_number_threads(pr)
            logger.info("{} {:.2f}MB {}% {}".format(name, memory_usage, cpu_usage, threads))
            table.append({"time": timestamp,
                          "memory_usage": memory_usage,
                          "threads_used": threads,
                          "cpu_usage": cpu_usage})
            time.sleep(int(args.collect_interval) / 1000)
    except psutil.NoSuchProcess:
        logger.info("Process terminated")
    report(table, args.report_name, args.report_path)
    pass
