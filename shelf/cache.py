from flask_cache import Cache
from flask_sqlalchemy import models_committed
import functools

class ShelfCache(Cache):
    def __init__(self, app=None, with_jinja2_ext=True, config=None, shelf=None):
        self.shelf = shelf if shelf else None
        super(ShelfCache, self).__init__(app, with_jinja2_ext, config)
        models_committed.connect(self.on_models_commited, sender=app)    

    smartcache = {}

    def on_models_commited(self, sender, changes):
        print "YOOO", self
        for model, change in changes:
            cls = model.__class__
            print model, change, cls
            #raise NotImplementedError
            if cls in self.smartcache:
                for f in self.smartcache[cls]:
                    self.delete_memoized(f)

    def memoize(self, timeout=None, make_name=None, unless=None, models=()):       
        def memoize(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                #: bypass cache
                if callable(unless) and unless() is True:
                    return f(*args, **kwargs)

                try:
                    cache_key = decorated_function.make_cache_key(f, *args, **kwargs)
                    rv = self.cache.get(cache_key)
                except Exception:
                    if current_app.debug:
                        raise
                    logger.exception("Exception possibly due to cache backend.")
                    return f(*args, **kwargs)

                if rv is None:
                    rv = f(*args, **kwargs)
                    try:
                        self.cache.set(cache_key, rv,
                                   timeout=decorated_function.cache_timeout)
                    except Exception:
                        if current_app.debug:
                            raise
                        logger.exception("Exception possibly due to cache backend.")
                        return f(*args, **kwargs)
                return rv

            decorated_function.uncached = f
            decorated_function.cache_timeout = timeout
            decorated_function.make_cache_key = self.memoize_make_cache_key(make_name)
            decorated_function.delete_memoized = lambda: self.delete_memoized(f)
            
            for m in models:
                if m not in self.smartcache:
                    self.smartcache[m] = [f,]
                elif f not in self.smartcache[m]:
                    self.smartcache[m].append(f)

            return decorated_function
        return memoize