import os
from app import create_app, db
from app.models import User, Role
from flask_migrate import Migrate
import sys
import click

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()
    Role.insert_roles()

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User)

# @app.cli.command()
# def test():
#     import unittest
#     tests = unittest.TestLoader().discover('tests')
#     unittest.TextTestRunner(verbosity=2).run(tests)

# starting of code for coverage report.
@app.cli.command()
@click.option('--coverage/--no-coverage', default=False, help='Run tests under code coverage.')
def test(coverage):
    """Runing the unit test"""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable]+sys.argv)

    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir,'tmp/coverage')
        COV.html_report(directory=covdir)
        print(f'HTML version: file://{covdir}/index.html')
        COV.erase()


# running the application under request profiler
@app.cli.command()
@click.option('--length',default=25,help='Number of functions to include in the profiler report.')
@click.option('--profile-dir',default=None,help="Directory where profiler data files are saved.")
def profile(length,profile_dir):
    """
    Starting the application under the code profile.
    """
    from werkzeug.middleware.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],profile_dir=profile_dir)
    
    app.run()


if __name__ == "__main__":
    app.run(debug=True)