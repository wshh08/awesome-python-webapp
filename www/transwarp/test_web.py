from web import get


@get('/test/:id')
def test():
    return 'OK'


test()
print test.__web_route__
print test.__web_method__
