## Installation Promgen On CentOS 7 (Updated - 11 Jan 2018)
This documentation outlines the steps required to install, configure and run promgen application on CentOS 7.4 minimal server.

### **Section 1 -  System Components Installation**

#### Step 1: Install the IUS repository
The IUS repository provides newer versions of some software in the official CentOS and Red Hat repositories. The IUS repository depends on the EPEL repository.
```
# yum -y install https://centos7.iuscommunity.org/ius-release.rpm
```

#### Step 2: Installation of  Git, Python 3.6 and All Requirements
```
# yum install python36u python36u-devel python36u-setuptools git gcc libxml2-devel libxslt-devel libffi-devel graphviz openssl-devel redhat-rpm-config -y
```

#### **Step 3: Install PIP**
```
easy_install-3.6 pip
```

#### **Step 4: Create Python Symlink**
```
# sudo ln -s /usr/bin/python3.6 /usr/bin/python3
```

#### **Step 4: Check Python 3 Version**
```
# python3 --version
```

### **Section 2 -  MySQL Database Configurations**

#### Step 1: Add MariaDB Yum Repository

Create the MariaDB repo file by issuing the following command
```
# sudo vi /etc/yum.repos.d/MariaDB.repo
```

Paste the following contents in MariaDB.repo and save the file
```
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/10.1/centos7-amd64
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
```

#### Step 2 - Install MariaDB Server, Client and Development Tools

```
# sudo yum install MariaDB-server MariaDB-devel MariaDB-client -y
```
Once the installation is complete, we'll start the MariaDB daemon with the following command:

```
# systemctl start mariadb
```
To ensure that the MariaDB daemon is started, issue the following command
```
# sudo systemctl status mariadb
```

Finally after ensuring that MariaDB is able to start successfully, we will use the systemctl enable command to ensure that MariaDB will start at boot.
```
# sudo systemctl enable mariadb
```

#### Step 3 - Securing the MariaDB Server
MariaDB includes a security script to modify some of the less secure default options for items such as remote root logins and sample users. Issue the following command to execute the security script:
```
# sudo mysql_secure_installation
```
The script provides a detailed explanation for every step. The first prompts asks for the root password, which hasn't been set so we'll press ENTER as it recommends. Next, we'll be prompted to set that root password, which we'll do.

Then, we'll accept all the security suggestions by pressing Y and then ENTER for the remaining prompts, which will remove anonymous users, disallow remote root login, remove the test database, and reload the privilege tables.

#### Step 4 - Create the promgen Database
Login as root user with the password set earlier at step 2
```
# mysql -u root -p
```

Create promgen database
```
> CREATE DATABASE promgen;
```

Exit MySQL command utility
```
> quit
```

### Section 3 -  Deploying Promgen Application

#### Step 1: Install the Required Python Packages
```
# pip3 install mysqlclient
```

#### Step 2: Clone the Git Repository
```
# git clone https://github.com/line/promgen.git
```

#### Step 3: Create promgen Setting Directory
Issue the following command to create the reuqired folder to store promgen settings
```
# sudo mkdir -p ~/.config/promgen
```
After creation of the folder, we configure the folder permission to allow for write access
```
# sudo chmod 777 ~/.config/promgen
```
Finally for ease of access, create a symlink to promgen setting directory from /promgen_cfg
```
# sudo ln -sf ~/.config/promgen /promgen_cfg
```

#### Step 4:  Generate The Required Configuration Files (CELERY_BROKER_URL, DATABASE_URL, promgen.yml, SECRET_KEY)
```
# promgen bootstrap
```

#### Step 5:  Install promgen from setup.py
```
# python3 setup.py install
```

#### Step 6:  Run Database Migrations
```
# promgen migrate
```

#### Step 7:  Create a Super User**
```
# promgen createsuperuser
```

#### Step 8:  Collect Static Files
```
# promgen collectstatic
```

#### Step 9:  Test the Application
```
promgen runserver 0.0.0.0:8000
```

### Section 4 - Web Server Deployment
A simple WSGI front end using gunicorn will be used for this guide and also Nginx will be the web server. We will also utilize supervisord to enable service persistence.

#### Step 1:  Nginx Web Server Installation

Install Nginx Using Yum Command
```
yum install nginx -y
```
Once the installation is complete, we'll start the nginx daemon with the following command:
```
# systemctl start nginx
```

To ensure that the nginx daemon is started, issue the following command
```
# sudo systemctl status nginx
```

Finally after ensuring that nginx is able to start successfully, we will use the systemctl enable command to ensure that nginx will start at boot.
```
# sudo systemctl enable nginx
```

Once nginx is installed, save the following configuration to /etc/nginx/sites-available/promgen.conf. Be sure to replace host name with the domain name or IP address of your installation.

Content of promgen.conf
```
server {
    listen 80;
    server_name host name;

  access_log /var/log/nginx/promgen.access_log main;
  error_log  /var/log/nginx/promgen.error_log;

      location /static/ {
        alias /pg_static/;
    }

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header X-Forwarded-Host $server_name;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Create a symlink in the sites-enabled directory to the configuration file you just created.
```
# cd /etc/nginx/conf.d/
# sudo ln -s /etc/nginx/sites-available/promgen.conf
```
Restart the nginx service to use the new configuration
```
# sudo systemctl nginx restart
```

#### Step 2:  Configure promgen static file location
Create a folder /pg_static/ and copy all the files from promgen collectstatic to this folder. Grant nginx read permission to this folder
```
# sudo cp -r /root/.cache/promgen/* /pg_static/
# sudo chown -R nginx /pg_static/*
# sudo chmod 755 /pg_static/* 
```

#### Step 3:  Installation of gunicorn package
```
pip3 install gunicorn
```

Save the following configuration in the root promgen installation path as gunicorn_config.py (e.g.  /promgen/gunicorn_config.py per our example installation).

Content of gunicorn_config.py
``` 
command = '/usr/bin/gunicorn'
bind = '127.0.0.1:8000'
workers = 3
``` 

#### Step 4:  Installation of supervisord
``` 
# sudo yum install supervisord -y
``` 

Once the installation is complete, we'll start the supervisord daemon with the following command:
```
# systemctl start nginx
```

To ensure that the supervisord daemon is started, issue the following command
```
# sudo systemctl status supervisord
```

Finally after ensuring that supervisord is able to start successfully, we will use the systemctl enable command to ensure that supervisord will start at boot.
```
# sudo systemctl enable supervisord
```

Once the service is verified to run correctly, add the following to /etc/supervisord.conf
``` 
[program:promgen]
command = gunicorn -c /promgen/gunicorn_config.py "promgen.wsgi:application" 
``` 

#### Step 5:  Restart the required services to take effect all the changes
``` 
# sudo systemctl supervisord restart
# sudo systemctl nginx restart
``` 

#### Step 6: Use promgen
On any web browser, navigate to http://hostname-of-promgen

Congratulation, promgen is successfully installed and configured
