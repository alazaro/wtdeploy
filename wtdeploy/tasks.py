import os.path

from fabric.api import env, run, local, sudo, cd

from wtdeploy.modules import fab_apache
from wtdeploy.modules import fab_mysql
from wtdeploy.modules import fab_django
from wtdeploy.modules import fab_python
from wtdeploy.modules import cron


def link_media():
    run("ln -s %s/app/media %s/app/media_link" % (env.main_app_deploy_folder, env.deploy_folder))


def reqs_install():
    """ install system requierements using apt-get """
    sudo("apt-get -y install mercurial git-core subversion libjpeg62 libjpeg62-dev")
    fab_apache.install(env.local_conf_folder)
    fab_python.install(env.local_conf_folder)
    fab_mysql.install(env.local_conf_folder)

def system_install():
    # install munin
    #fab_munin.install(env.local_conf_folder)
    # directorio
    # database
    fab_mysql.create_database(env.database_name)
    fab_mysql.drop_user(env.database_user)
    fab_mysql.create_user(env.database_user, env.database_pass)
    fab_mysql.user_perms(env.database_user, env.database_name)


def install_app():
    """ install django app """
    run("mkdir -p %s" % env.deploy_folder)
    fab_django.prepare_env(env.local_conf_folder, env.deploy_folder)
    update_conf()
    if env.link_media:
        link_media()
    deploy()
    with cd(env.deploy_folder):
        fab_django.create_admin()

def clean_app():
    run("rm -rf %s" % env.deploy_folder)

def install():
    """ install system requirements and create basic app setup """
    reqs_install()
    system_install()
    install_app()

def create_admin():
    with cd(env.deploy_folder):
        fab_django.create_admin()

def upgrade_env():
    """ upgrade virtual env """
    fab_django.create_virtualenv(env.local_conf_folder, env.deploy_folder)
    
def update_conf():
    fab_apache.copy_conf_files(env.local_conf_folder, env.deploy_folder)
    fab_django.copy_conf_files(env.local_conf_folder, env.deploy_folder, env.is_mobile)
    cron.copy_conf_files(env.local_conf_folder, env.deploy_folder)
    
def update_index():
  with cd(env.deploy_folder):
    fab_django.update_index()


def deploy():
  with cd(env.deploy_folder):
    fab_django.deploy()
  fab_django.copy_conf_files(env.local_conf_folder, env.deploy_folder, env.is_mobile)
  with cd(env.deploy_folder):
    fab_django.syncdb()
  update_conf()
  fab_django.restart()
  # in theory apache restart is not needed...
  fab_apache.restart()
  deploy_info()


def deploy_info():
    run("date > %s/app/media/deploy_info.txt" % (env.deploy_folder))
    run("svn info %s/app >> %s/app/media/deploy_info.txt" % (env.deploy_folder,env.deploy_folder))

def quick_deploy():
  """ this target run a quick deploy, only update source from repository and restart app.wsgi
      this target do NOT run migrations, upload configurationes files or restart apache
  """
  with cd(env.deploy_folder):
    fab_django.deploy()
  fab_django.restart()
  # please, read deploy function comments to know what this cmd does
  with cd(env.deploy_folder):
    fab_django.load_fixture('youtube_regexp')
  deploy_info()

def get_database_dump():
    """ download a database dump from server """
    fab_mysql.get_dump(env.database_name, env.database_user, env.database_pass, 'database_%s.sql.gz' % env.host)

def load_initial_data():
    """ load fixtures """
    with cd(env.deploy_folder):
        fab_django.load_data()

def backup():
    home = os.getenv('HOME')
    bak_dir = home + '/backup/%(host)s' % env
    local("mkdir -p %s" % bak_dir)
    fab_mysql.get_dump(env.database_name, env.database_user, env.database_pass, '%s/database.sql.gz' % bak_dir)
    local('rsync -avz -e ssh %(user)s@%(host)s:%(deploy_folder)s/app/media/' % env +  ' %s/media/' % bak_dir)
    local("date > %s/backup_info.txt" % bak_dir)

