import argparse
from utils.predict_res import local_test, remote_control

if (__name__ == '__main__'):
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument(
        '-f', '--flag',
        default='remote',
        help='local: test.npz, remote:')
    argparser.add_argument(
        '-t', ',--target_ip',
        default='ubuntu.hwanmoo.kr',
        help='IP of the host server (default: ubuntu.hwanmoo.kr)')
    argparser.add_argument(
        '-r', '--redis_address',
        metavar='R',
        default='redis.hwanmoo.kr',
        help='Redis address (default: redis.hwanmoo.kr)')

    args = argparser.parse_args()

    if args.flag == 'local':
        local_test()
    else:
        remote_control()
