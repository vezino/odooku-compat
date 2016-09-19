include /odooku/env.mk

PORT=8000
NUM=1
BUILDPACK_URL=https://github.com/adaptivdesign/odooku-buildpack

UNIQUE:=$(shell cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 32 | head -n 1)
CMD:=/bin/bash

NEW_DATABASE_URL:=postgres://odoo:odoo@localhost:5432/${UNIQUE}
NEW_ADMIN_PASSWORD:=${UNIQUE}
NEW_REDIS_URL:=redis://localhost:6379
NEW_S3_BUCKET:=${UNIQUE}
NEW_ODOOKU_CDN:=0


define NEW_ENV
DATABASE_URL:=${NEW_DATABASE_URL}
ADMIN_PASSWORD:=${NEW_ADMIN_PASSWORD}
REDIS_URL:=${NEW_REDIS_URL}
S3_BUCKET:=${NEW_S3_BUCKET}
ODOOKU_CDN:=${NEW_ODOOKU_CDN}
endef
export NEW_ENV


define RUN_ARGS
--net host \
-v /vagrant:/vagrant \
-v /odooku:/odooku \
-e DATABASE_URL=${DATABASE_URL} \
-e REDIS_URL=${REDIS_URL} \
-e S3_BUCKET=${S3_BUCKET} \
-e S3_ENDPOINT_URL=http://localhost:4569 \
-e S3_CUSTOM_DOMAIN=http://${S3_BUCKET}.localhost:4569 \
-e AWS_ACCESS_KEY_ID=foobar \
-e AWS_SECRET_ACCESS_KEY=foobar \
-e PORT=${PORT} \
-e ODOOKU_DEBUG=1 \
-e ODOOKU_STATSD_HOST=127.0.0.1:8125 \
-e ODOOKU_ADMIN_PASSWORD=${ADMIN_PASSWORD} \
-e ODOOKU_CDN=${ODOOKU_CDN} \
gliderlabs/herokuish
endef


define BASH_INIT
/bin/herokuish slug import < /odooku/slug.tar.gz \
;/app/.heroku/odoo/bin/pip install --disable-pip-version-check --upgrade -e /vagrant/runtime/. &>/dev/null \
;cp -a /vagrant/addons/. /app/.heroku/odoo/compat_addons/ \
;cp -a /vagrant/patch/addons/. /app/.heroku/odoo/addons/ \
;cp -a /vagrant/patch/openerp/. /app/.heroku/odoo/lib/python2.7/site-packages/openerp/ \
&& export ODOOKU_DEV=true
endef


# Parse database url's
db_user=$(shell echo ${DATABASE_URL} | sed -e 's/^postgres:\/\/\(.*\):.*@.*:.*\/.*$$/\1/')
db_password=$(shell echo ${DATABASE_URL} | sed -e 's/^postgres:\/\/.*:\(.*\)@.*:.*\/.*$$/\1/')
db_host=$(shell echo ${DATABASE_URL} | sed -e 's/^postgres:\/\/.*:.*@\(.*\):.*\/.*$$/\1/')
db_port=$(shell echo ${DATABASE_URL} | sed -e 's/^postgres:\/\/.*:.*@.*:\(.*\)\/.*$$/\1/')
db_name=$(shell echo ${DATABASE_URL} | sed -e 's/^postgres:\/\/.*:.*@.*:.*\/\(.*\)$$/\1/')
new_db_user=$(shell echo ${NEW_DATABASE_URL} | sed -e 's/^postgres:\/\/\(.*\):.*@.*:.*\/.*$$/\1/')
new_db_password=$(shell echo ${NEW_DATABASE_URL} | sed -e 's/^postgres:\/\/.*:\(.*\)@.*:.*\/.*$$/\1/')
new_db_host=$(shell echo ${NEW_DATABASE_URL} | sed -e 's/^postgres:\/\/.*:.*@\(.*\):.*\/.*$$/\1/')
new_db_port=$(shell echo ${NEW_DATABASE_URL} | sed -e 's/^postgres:\/\/.*:.*@.*:\(.*\)\/.*$$/\1/')
new_db_name=$(shell echo ${NEW_DATABASE_URL} | sed -e 's/^postgres:\/\/.*:.*@.*:.*\/\(.*\)$$/\1/')


new-env:
	@echo "Updating env"
	@echo "$$NEW_ENV" > /odooku/env.mk
	@echo "Creating new database ${new_db_name}"
	@docker run \
		--rm \
		-i \
		--net host \
		-e PGPASSWORD=${new_db_password} \
		postgres:9.5 \
		createdb -U ${new_db_user} -w -h ${new_db_host} -p ${new_db_port} ${new_db_name}

	@echo "Admin password: ${NEW_ADMIN_PASSWORD}"


build:
	@echo "Using local commit $$(git rev-parse HEAD)"
	-@rm -rf /odooku/app
	@mkdir -p /odooku/app
	@git archive --format=tar HEAD | (cd /odooku/app/ && tar xf -)
	@docker run \
		--rm \
		-it \
		-e BUILDPACK_URL=${BUILDPACK_URL} \
		-v /odooku/app:/tmp/app \
		-v /odooku/cache:/tmp/cache \
		-v /odooku:/odooku \
		gliderlabs/herokuish \
		bin/bash -c \
			"/bin/herokuish buildpack build \
			&& IMPORT_PATH=/nosuchpath /bin/herokuish slug generate \
			&& /bin/herokuish slug export > /odooku/slug.tar.gz"


run-web:
	-@docker rm -f -v web.1
	@docker run \
		-d \
		--name web.1 \
		${RUN_ARGS} \
		bin/bash -c \
			"${BASH_INIT} \
			;USER=herokuishuser /bin/herokuish procfile start web"
	@docker logs -f web.1


run-worker:
	-@docker rm -f  -v worker.1
	@docker run \
		-d \
		--name worker.1 \
		${RUN_ARGS} \
		bin/bash -c \
			"${BASH_INIT} \
			;USER=herokuishuser /bin/herokuish procfile start worker"
	@docker logs -f worker.1


shell:
	@docker run \
		--rm -it \
		--name shell \
		${RUN_ARGS} \
		bin/bash -c \
			"${BASH_INIT} \
			;USER=herokuishuser /bin/herokuish procfile exec ${CMD}"


run:
	@docker run \
		--rm -i \
		--name run \
		${RUN_ARGS} \
		bin/bash -c \
			"${BASH_INIT} \
			;USER=herokuishuser /bin/herokuish procfile exec ${CMD}"


psql:
	@docker run \
		--rm \
		-it \
		--net host \
		-e PGPASSWORD=${db_password} \
		postgres:9.5 \
		psql -U ${db_user} -w -h ${db_host} -p ${db_port} -d ${db_name}
