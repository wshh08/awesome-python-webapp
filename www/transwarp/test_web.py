import web


# static = web.StaticFileRoute('FUCK')
wsgi = web.WSGIApplication()
wsgi.run(9000)
