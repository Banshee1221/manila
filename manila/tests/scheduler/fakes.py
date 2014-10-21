# Copyright 2011 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Fakes For Scheduler tests.
"""

from oslo.utils import timeutils
import six

from manila.scheduler import filter_scheduler
from manila.scheduler import host_manager


SHARE_SERVICES = [
    dict(id=1, host='host1', topic='share', disabled=False,
         availability_zone='zone1', updated_at=timeutils.utcnow()),
    dict(id=2, host='host2', topic='share', disabled=False,
         availability_zone='zone1', updated_at=timeutils.utcnow()),
    dict(id=3, host='host3', topic='share', disabled=False,
         availability_zone='zone2', updated_at=timeutils.utcnow()),
    dict(id=4, host='host4', topic='share', disabled=False,
         availability_zone='zone3', updated_at=timeutils.utcnow()),
    # service on host5 is disabled
    dict(id=5, host='host5', topic='share', disabled=True,
         availability_zone='zone4', updated_at=timeutils.utcnow()),
]


class FakeFilterScheduler(filter_scheduler.FilterScheduler):
    def __init__(self, *args, **kwargs):
        super(FakeFilterScheduler, self).__init__(*args, **kwargs)
        self.host_manager = host_manager.HostManager()


class FakeHostManager(host_manager.HostManager):
    def __init__(self):
        super(FakeHostManager, self).__init__()

        self.service_states = {
            'host1': {'total_capacity_gb': 1024,
                      'free_capacity_gb': 1024,
                      'reserved_percentage': 10,
                      'timestamp': None},
            'host2': {'total_capacity_gb': 2048,
                      'free_capacity_gb': 300,
                      'reserved_percentage': 10,
                      'timestamp': None},
            'host3': {'total_capacity_gb': 512,
                      'free_capacity_gb': 512,
                      'reserved_percentage': 0,
                      'timestamp': None},
            'host4': {'total_capacity_gb': 2048,
                      'free_capacity_gb': 200,
                      'reserved_percentage': 5,
                      'timestamp': None},
        }


class FakeHostState(host_manager.HostState):
    def __init__(self, host, attribute_dict):
        super(FakeHostState, self).__init__(host)
        for (key, val) in six.iteritems(attribute_dict):
            setattr(self, key, val)


def mock_host_manager_db_calls(mock_obj, disabled=None):
    services = [
        dict(id=1, host='host1', topic='share', disabled=False,
             availability_zone='zone1', updated_at=timeutils.utcnow()),
        dict(id=2, host='host2', topic='share', disabled=False,
             availability_zone='zone1', updated_at=timeutils.utcnow()),
        dict(id=3, host='host3', topic='share', disabled=False,
             availability_zone='zone2', updated_at=timeutils.utcnow()),
        dict(id=4, host='host4', topic='share', disabled=False,
             availability_zone='zone3', updated_at=timeutils.utcnow()),
        # service on host5 is disabled
        dict(id=5, host='host5', topic='share', disabled=True,
             availability_zone='zone4', updated_at=timeutils.utcnow()),
    ]
    if disabled is None:
        mock_obj.return_value = services
    else:
        mock_obj.return_value = [service for service in services
                                 if service['disabled'] == disabled]
