build() {
	declare desc="Build the Herokuish Docker image"
	declare commit=`(git rev-parse HEAD)`
	title "Starting build"
	echo "Using local commit $commit" | indent
	rm -rf $app_path
	mkdir -p $app_path
	git archive --format=tar $commit | (cd $app_path/ && tar xf -)
  docker run \
		--rm \
		-e BUILDPACK_URL=$buildpack_path \
		-v $local_path:$local_path \
		-v $app_path:/tmp/app \
		-v $cache_path:/tmp/cache \
		gliderlabs/herokuish \
		bin/bash -c \
			"/bin/herokuish buildpack build \
			&& IMPORT_PATH=/nosuchpath /bin/herokuish slug generate \
			&& /bin/herokuish slug export > $slug_path"
}
