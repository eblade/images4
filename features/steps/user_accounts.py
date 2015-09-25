from behave import *

from images.user import authenticate

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
