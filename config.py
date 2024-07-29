import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY','jsdfioisjthslkamcnfjrisl')
    MAIL_SERVER = os.environ.get('MAIL_SERVER','smtp.googlemail.com') 
    MAIL_PORT = int(os.environ.get('MAIL_PORT','587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS','true').lower() in ['true','on','1','True','TRUE']   
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    NKBLOG_MAIL_SUBJECT_PREFIX = '[Nkblog]'
    NKBLOG_MAIL_SENDER = 'Nkblog Admin nk@nkblog.com'
    NKBLOG_ADMIN = os.environ.get('NKBLOG_ADMIN')
    NKBLOG_POSTS_PER_PAGE = os.environ.get('NKBLOG_POSTS_PER_PAGE')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    NKBLOG_COMMENTS_PER_PAGE = os.environ.get('NKBLOG_COMMENTS_PER_PAGE')
    FLASK_COVERAGE = os.environ.get('FLASK_COVERAGE')
    SERVER_NAME = os.environ.get('SERVER_NAME') # '127.0.0.1:5000'
    SQLALCHEMY_RECORD_QUERIES = True
    NKBLOG_SLOW_DB_QUERY_TIME = 0.5
    # DEBUG = os.environ.get('DEBUG','1').lower() in ['true','on','1','True','TRUE']

    # Flask-Profiler configuration
    FLASK_PROFILER = {
        "enabled": True,
        "storage": {
            "engine": "sqlite"
        },
        "basicAuth": {
            "enabled": False
        },
        "ignore": [
            "^/static/.*"
        ]
    }

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///'+os.path.join(basedir,'data-dev.sqlite')
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite://'
    WTF_CSRF_ENABLED = False  # turned off csrf protection
    
class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///'+os.path.join(basedir,'data.sqlite')

    # sending mail if any error occurs
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email to admin
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None

        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        
        mail_handler = SMTPHandler(mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
                                   fromaddr=cls.NKBLOG_MAIL_SENDER,
                                   toaddrs=[cls.NKBLOG_ADMIN],
                                   subject=cls.NKBLOG_MAIL_SUBJECT_PREFIX+'Application Error',
                                   credentials=credentials,
                                   secure=secure)
        
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

class DockerConfig(ProductionConfig):
    @classmethod
    def init_app(cls,app):
        ProductionConfig.init_app(app)

        # log to stder
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

config = {

    'development' : DevelopmentConfig,
    'testing' : TestingConfig,
    'production' : ProductionConfig,
    'default' : DevelopmentConfig,
    'docker' : DockerConfig
}