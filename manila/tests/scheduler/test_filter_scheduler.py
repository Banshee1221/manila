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
Tests For Filter Scheduler.
"""
import mock

from manila import context
from manila import exception
from manila.scheduler import filter_scheduler
from manila.scheduler import host_manager
from manila.tests.scheduler import fakes
from manila.tests.scheduler import test_scheduler


class FilterSchedulerTestCase(test_scheduler.SchedulerTestCase):
    """Test case for Filter Scheduler."""

    driver_cls = filter_scheduler.FilterScheduler

    def test_create_share_no_hosts(self):
        # Ensure empty hosts/child_zones result in NoValidHosts exception.
        sched = fakes.FakeFilterScheduler()
        fake_context = context.RequestContext('user', 'project')
        request_spec = {
            'share_properties': {'project_id': 1, 'size': 1},
            'share_type': {'name': 'NFS'},
            'share_id': ['fake-id1'],
        }
        self.assertRaises(exception.NoValidHost, sched.schedule_create_share,
                          fake_context, request_spec, {})

    @mock.patch('manila.scheduler.host_manager.HostManager.'
                'get_all_host_states_share')
    def test_create_share_non_admin(self, _mock_get_all_host_states):
        # Test creating a volume locally using create_volume, passing
        # a non-admin context. DB actions should work.
        self.was_admin = False

        def fake_get(context, *args, **kwargs):
            # Make sure this is called with admin context, even though
            # we're using user context below.
            self.was_admin = context.is_admin
            return {}

        sched = fakes.FakeFilterScheduler()
        _mock_get_all_host_states.side_effect = fake_get
        fake_context = context.RequestContext('user', 'project')
        request_spec = {
            'share_properties': {'project_id': 1, 'size': 1},
            'share_type': {'name': 'NFS'},
            'share_id': ['fake-id1'],
        }
        self.assertRaises(exception.NoValidHost, sched.schedule_create_share,
                          fake_context, request_spec, {})
        self.assertTrue(self.was_admin)

    @mock.patch('manila.db.service_get_all_by_topic')
    def test_schedule_happy_day_share(self, _mock_service_get_all_by_topic):
        # Make sure there's nothing glaringly wrong with _schedule()
        # by doing a happy day pass through.
        sched = fakes.FakeFilterScheduler()
        sched.host_manager = fakes.FakeHostManager()
        fake_context = context.RequestContext('user', 'project',
                                              is_admin=True)
        fakes.mock_host_manager_db_calls(_mock_service_get_all_by_topic)
        request_spec = {
            'share_type': {'name': 'NFS'},
            'share_properties': {'project_id': 1, 'size': 1},
        }
        weighed_host = sched._schedule_share(fake_context, request_spec, {})
        self.assertIsNotNone(weighed_host.obj)
        self.assertTrue(_mock_service_get_all_by_topic.called)

    def test_max_attempts(self):
        self.flags(scheduler_max_attempts=4)
        sched = fakes.FakeFilterScheduler()
        self.assertEqual(4, sched._max_attempts())

    def test_invalid_max_attempts(self):
        self.flags(scheduler_max_attempts=0)
        self.assertRaises(exception.InvalidParameterValue,
                          fakes.FakeFilterScheduler)

    def test_retry_disabled(self):
        # Retry info should not get populated when re-scheduling is off.
        self.flags(scheduler_max_attempts=1)
        sched = fakes.FakeFilterScheduler()
        request_spec = {
            'share_type': {'name': 'iSCSI'},
            'share_properties': {'project_id': 1, 'size': 1},
        }
        filter_properties = {}
        sched._schedule_share(self.context, request_spec,
                              filter_properties=filter_properties)
        # Should not have retry info in the populated filter properties.
        self.assertNotIn("retry", filter_properties)

    def test_retry_attempt_one(self):
        # Test retry logic on initial scheduling attempt.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeFilterScheduler()
        request_spec = {
            'share_type': {'name': 'iSCSI'},
            'share_properties': {'project_id': 1, 'size': 1},
        }
        filter_properties = {}
        sched._schedule_share(self.context, request_spec,
                              filter_properties=filter_properties)
        num_attempts = filter_properties['retry']['num_attempts']
        self.assertEqual(1, num_attempts)

    def test_retry_attempt_two(self):
        # Test retry logic when re-scheduling.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeFilterScheduler()
        request_spec = {
            'share_type': {'name': 'iSCSI'},
            'share_properties': {'project_id': 1, 'size': 1},
        }
        retry = dict(num_attempts=1)
        filter_properties = dict(retry=retry)
        sched._schedule_share(self.context, request_spec,
                              filter_properties=filter_properties)
        num_attempts = filter_properties['retry']['num_attempts']
        self.assertEqual(2, num_attempts)

    def test_retry_exceeded_max_attempts(self):
        # Test for necessary explosion when max retries is exceeded.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeFilterScheduler()
        request_spec = {
            'share_type': {'name': 'iSCSI'},
            'share_properties': {'project_id': 1, 'size': 1},
        }
        retry = dict(num_attempts=2)
        filter_properties = dict(retry=retry)
        self.assertRaises(exception.NoValidHost, sched._schedule_share,
                          self.context, request_spec,
                          filter_properties=filter_properties)

    def test_add_retry_host(self):
        retry = dict(num_attempts=1, hosts=[])
        filter_properties = dict(retry=retry)
        host = "fakehost"
        sched = fakes.FakeFilterScheduler()
        sched._add_retry_host(filter_properties, host)
        hosts = filter_properties['retry']['hosts']
        self.assertEqual(1, len(hosts))
        self.assertEqual(host, hosts[0])

    def test_post_select_populate(self):
        # Test addition of certain filter props after a node is selected.
        retry = {'hosts': [], 'num_attempts': 1}
        filter_properties = {'retry': retry}
        sched = fakes.FakeFilterScheduler()
        host_state = host_manager.HostState('host')
        host_state.total_capacity_gb = 1024
        sched._post_select_populate_filter_properties(filter_properties,
                                                      host_state)
        self.assertEqual('host',
                         filter_properties['retry']['hosts'][0])
        self.assertEqual(1024, host_state.total_capacity_gb)
