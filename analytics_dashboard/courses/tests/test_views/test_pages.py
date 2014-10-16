import json
from ddt import data, ddt

import mock
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
import analyticsclient.constants.activity_type as AT
from analyticsclient.exceptions import NotFoundError

from courses.tests.test_views import ViewTestMixin, DEMO_COURSE_ID, DEPRECATED_DEMO_COURSE_ID
from courses.exceptions import PermissionsRetrievalFailedError
from courses.tests.test_middleware import MiddlewareAssertionMixin
from courses.tests import utils


@ddt
class CourseViewTestMixin(ViewTestMixin):
    presenter_method = None

    def assertPrimaryNav(self, nav, course_id):
        raise NotImplementedError

    def assertSecondaryNavs(self, nav, course_id):
        raise NotImplementedError

    @mock.patch('courses.views.CourseValidMixin.is_valid_course', mock.Mock(return_value=False))
    def test_invalid_course(self):
        course_id = 'fakeOrg/soFake/Fake_Course'
        self.grant_permission(self.user, course_id)
        path = reverse(self.viewname, kwargs={'course_id': course_id})

        response = self.client.get(path, follow=True)
        self.assertEqual(response.status_code, 404)

    def assertViewIsValid(self, course_id):
        raise NotImplementedError

    @data(DEMO_COURSE_ID, DEPRECATED_DEMO_COURSE_ID)
    def test_valid_course(self, course_id):
        self.assertViewIsValid(course_id)

    def assertValidMissingDataContext(self, context):
        raise NotImplementedError

    @data(DEMO_COURSE_ID, DEPRECATED_DEMO_COURSE_ID)
    def test_missing_data(self, course_id):
        with mock.patch(self.presenter_method, mock.Mock(side_effect=NotFoundError)):
            response = self.client.get(self.path(course_id))
            context = response.context

        self.assertValidMissingDataContext(context)


# pylint: disable=abstract-method
class CourseEnrollmentViewTestMixin(CourseViewTestMixin):
    active_secondary_nav_label = None
    api_method = 'analyticsclient.course.Course.enrollment'

    def assertPrimaryNav(self, nav, course_id):
        expected = {
            'icon': 'fa-child',
            'href': reverse('courses:enrollment_activity', kwargs={'course_id': course_id}),
            'label': _('Enrollment'),
            'name': 'enrollment'
        }
        self.assertDictEqual(nav, expected)

    def assertSecondaryNavs(self, nav, course_id):
        reverse_kwargs = {'course_id': course_id}
        expected = [
            {'name': 'activity', 'label': _('Activity'),
             'href': reverse('courses:enrollment_activity', kwargs=reverse_kwargs)},
            {'name': 'geography', 'label': _('Geography'),
             'href': reverse('courses:enrollment_geography', kwargs=reverse_kwargs)}
        ]

        for item in expected:
            if item['label'] == self.active_secondary_nav_label:
                item['active'] = True
                item['href'] = '#'
            else:
                item['active'] = False

        self.assertListEqual(nav, expected)

    def get_mock_data(self, course_id):
        return utils.get_mock_api_enrollment_data(course_id)


# pylint: disable=abstract-method
class CourseEngagementViewTestMixin(CourseViewTestMixin):
    api_method = 'analyticsclient.course.Course.activity'

    def get_mock_data(self, course_id):
        return utils.mock_course_activity(course_id)

    def assertPrimaryNav(self, nav, course_id):
        expected = {
            'icon': 'fa-bar-chart',
            'href': reverse('courses:engagement_content', kwargs={'course_id': course_id}),
            'label': _('Engagement'),
            'name': 'engagement'
        }
        self.assertDictEqual(nav, expected)

    def assertSecondaryNavs(self, nav, course_id):
        expected = [{'active': True, 'name': 'content', 'label': _('Content'), 'href': '#'}]
        self.assertListEqual(nav, expected)


@ddt
class CourseEngagementContentViewTests(CourseEngagementViewTestMixin, TestCase):
    viewname = 'courses:engagement_content'
    presenter_method = 'courses.presenters.CourseEngagementPresenter.get_summary_and_trend_data'

    def assertViewIsValid(self, course_id):
        rv = utils.mock_engagement_activity_summary_and_trend_data()
        with mock.patch(self.presenter_method, mock.Mock(return_value=rv)):
            response = self.client.get(self.path(course_id))

            # make sure that we get a 200
            self.assertEqual(response.status_code, 200)

            # check page title
            self.assertEqual(response.context['page_title'], 'Engagement Content')

            # make sure the summary numbers are correct
            self.assertEqual(response.context['summary'][AT.ANY], 100)
            self.assertEqual(response.context['summary'][AT.ATTEMPTED_PROBLEM], 301)
            self.assertEqual(response.context['summary'][AT.PLAYED_VIDEO], 1000)
            self.assertEqual(response.context['summary'][AT.POSTED_FORUM], 0)

            # check to make sure the activity trends are correct
            trends = response.context['js_data']['course']['engagementTrends']
            self.assertEqual(len(trends), 2)
            expected = {
                'weekEnding': '2013-01-08',
                AT.ANY: 100,
                AT.ATTEMPTED_PROBLEM: 301,
                AT.PLAYED_VIDEO: 1000,
                AT.POSTED_FORUM: 0
            }
            self.assertDictEqual(trends[0], expected)

            expected = {
                'weekEnding': '2013-01-01',
                AT.ANY: 1000,
                AT.ATTEMPTED_PROBLEM: 0,
                AT.PLAYED_VIDEO: 10000,
                AT.POSTED_FORUM: 45
            }
            self.assertDictEqual(trends[1], expected)

            self.assertPrimaryNav(response.context['primary_nav_item'], course_id)
            self.assertSecondaryNavs(response.context['secondary_nav_items'], course_id)

    def assertValidMissingDataContext(self, context):
        # summary and engagementTrends should evaluate to falsy values, which the
        # template evaluates to render error messages
        self.assertIsNone(context['summary'])
        self.assertIsNone(context['js_data']['course']['engagementTrends'])


@ddt
class CourseEnrollmentActivityViewTests(CourseEnrollmentViewTestMixin, TestCase):
    viewname = 'courses:enrollment_activity'
    active_secondary_nav_label = 'Activity'
    presenter_method = 'courses.presenters.CourseEnrollmentPresenter.get_summary_and_trend_data'

    def assertViewIsValid(self, course_id):
        summary, enrollment_data = utils.get_mock_enrollment_summary_and_trend(course_id)
        rv = summary, enrollment_data
        with mock.patch(self.presenter_method, return_value=rv):
            response = self.client.get(self.path(course_id))

        context = response.context

        # Ensure we get a valid HTTP status
        self.assertEqual(response.status_code, 200)

        # check page title
        self.assertEqual(context['page_title'], 'Enrollment Activity')

        # make sure the summary numbers are correct
        self.assertDictEqual(context['summary'], summary)

        # make sure the trend is correct
        page_data = json.loads(context['page_data'])
        trend_data = page_data['course']['enrollmentTrends']
        expected = enrollment_data
        self.assertListEqual(trend_data, expected)

        self.assertPrimaryNav(context['primary_nav_item'], course_id)
        self.assertSecondaryNavs(context['secondary_nav_items'], course_id)

    def assertValidMissingDataContext(self, context):
        self.assertIsNone(context['summary'])
        self.assertIsNone(context['js_data']['course']['enrollmentTrends'])


@ddt
class CourseEnrollmentGeographyViewTests(CourseEnrollmentViewTestMixin, TestCase):
    viewname = 'courses:enrollment_geography'
    active_secondary_nav_label = 'Geography'
    presenter_method = 'courses.presenters.CourseEnrollmentPresenter.get_geography_data'

    def get_mock_data(self, course_id):
        return utils.get_mock_api_enrollment_geography_data(course_id)

    def assertViewIsValid(self, course_id):
        with mock.patch(self.presenter_method, return_value=utils.get_mock_presenter_enrollment_geography_data()):
            response = self.client.get(self.path(course_id))
            context = response.context

            # make sure that we get a 200
            self.assertEqual(response.status_code, 200)

            # check page title
            self.assertEqual(context['page_title'], 'Enrollment Geography')

            page_data = json.loads(context['page_data'])
            _summary, expected_data = utils.get_mock_presenter_enrollment_geography_data()
            self.assertEqual(page_data['course']['enrollmentByCountry'], expected_data)

    def assertValidMissingDataContext(self, context):
        self.assertIsNone(context['update_message'])
        self.assertIsNone(context['js_data']['course']['enrollmentByCountry'])


@ddt
class CourseHomeViewTests(CourseEnrollmentViewTestMixin, TestCase):
    """
    Course homepage

    We do not actually have a course homepage, so redirect to the enrollment activity page.
    """
    viewname = 'courses:home'

    def assertViewIsValid(self, course_id):
        response = self.client.get(self.path(course_id))

        expected_url = reverse('courses:enrollment_activity', kwargs={'course_id': course_id})
        self.assertRedirectsNoFollow(response, expected_url)

    @data(DEMO_COURSE_ID, DEPRECATED_DEMO_COURSE_ID)
    def test_missing_data(self, course_id):
        self.skipTest('The course homepage simply redirects to the enrollment activity page.')


@ddt
class CourseIndexViewTests(ViewTestMixin, MiddlewareAssertionMixin, TestCase):
    viewname = 'courses:index'

    @data(DEMO_COURSE_ID, DEPRECATED_DEMO_COURSE_ID)
    def test_get(self, course_id):
        # If no course permissions, raise an error.
        self.grant_permission(self.user)
        response = self.client.get(self.path())
        self.assertEqual(response.status_code, 403)

        # With permissions, the course list should include the accessible course(s)
        self.grant_permission(self.user, course_id)
        response = self.client.get(self.path())
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.context['courses'], [course_id])

    @mock.patch('courses.permissions.get_user_course_permissions',
                mock.Mock(side_effect=PermissionsRetrievalFailedError))
    def test_get_with_permissions_error(self):
        response = self.client.get(self.path())
        self.assertIsPermissionsRetrievalFailedResponse(response)
