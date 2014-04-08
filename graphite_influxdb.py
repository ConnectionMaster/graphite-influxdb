try:
    from graphite_api.intervals import Interval, IntervalSet
    from graphite_api.node import LeafNode, BranchNode
except ImportError:
    from graphite.intervals import Interval, IntervalSet
    from graphite.node import LeafNode, BranchNode

from influxdb import InfluxDBClient


def config_to_client(config=None):
    return InfluxDBClient(host, port, user, passw, db)


class InfluxdbReader(object):
    __slots__ = ('path', 'client')

    def __init__(self, client, path):
        self.client = client
        self.path = path

    def fetch(self, start_time, end_time):
        data = self.client.query("select time, value from %s where time > %ds and time < %ds order asc" % (self.path, start_time, end_time))
        datapoints = []
        start = 0
        end = 0
        step = 0
        try:
            points = data[0]['points']
            start = points[0][0]
            end = points[-1][0]
            step = points[1][0] - start
            datapoints = [p[2] for p in points]
        except Exception:
            pass
        time_info = start, end, step
        return time_info, datapoints

    def get_intervals(self):
        last_data = self.client.query("select * from %s limit 1" % self.path)
        first_data = self.client.query("select * from %s limit 1 order asc" % self.path)
        last = 0
        first = 0
        try:
            last = last_data[0]['points'][0][0]
            first = first_data[0]['points'][0][0]
        except Exception:
            pass
        return IntervalSet([Interval(first, last)])


class InfluxdbFinder(object):
    __slots__ = ('client')

    def __init__(self, config=None):
        self.client = config_to_client(config)

    def find_nodes(self, query):
        # query.pattern is basically regex, though * should become [^\.]+ and . \.
        # but list series doesn't support pattern matching/regex yet
        series = self.client.query("list series")
        series = [s['name'] for s in series]
        seen_branches = set()
        # for leaf "a.b.c" we should yield branches "a" and "a.b"
        for s in series:
            yield LeafNode(s, InfluxdbReader(self.client, s))
            branch = s
            while branch != '' and branch not in seen_branches:
                yield BranchNode(branch)
                seen_branches.add(branch)
                branch = branch.rpartition('.')[0]
