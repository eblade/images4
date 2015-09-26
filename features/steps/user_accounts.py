from behave import *

from bottle import request
from images.user import authenticate, current_is_user, current_is_admin, current_is_guest

@given('the username is "{user}"')
def step_impl(context, user):
    context.user = user

@given('the password is "{password}"')
def step_impl(context, password):
    context.password = password

@when('the user tries to log in')
def step_impl(context):
    context.logged_in = authenticate(context.user, context.password)

@then('the login should {result}')
def step_impl(context, result):
    if result == 'succeed':
        assert context.logged_in
    elif result == 'fail':
        assert not context.logged_in

@then('the session should belong to logged in user')
def step_impl(context):
    assert request.user.name == context.user

@then('there should not be a session')
def step_impl(context):
    assert getattr(request, 'user', None) is None

@then('the session have user rights')
def step_impl(context):
    assert current_is_user()

@then('the session have admin rights')
def step_impl(context):
    assert current_is_admin()

@then('the session have guest rights')
def step_impl(context):
    assert current_is_guest()

