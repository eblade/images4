import shutil, os

def before_all(context):
    context.tear_down_session = []

def after_all(context):
    for tear_down in context.tear_down_session:
        tear_down(context)

def before_scenario(context, scenario):
    context.tear_down_scenario = []
    
def after_scenario(context, scenario):
    for tear_down in context.tear_down_scenario:
        tear_down(context)
