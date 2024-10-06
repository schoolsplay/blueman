#!/usr/bin/env bash

echo "Did you run the autogen.sh with the btp options? [y\n]"
read -r response
if [ "$response" != "y" ]; then
    echo "Please run the autogen.sh with the btp options."
    exit 1
fi

echo "Did you run make & make install? [y\n]"
read -r response
if [ "$response" != "y" ]; then
    echo "Please run make & make install."
    exit 1
fi

mkdir -p .venv3.8/lib/python3.8/site-packages/data
cp -rf ~/Github/SchoolsplayRepos/blueman/data/ui .venv3.8/lib/python3.8/site-packages/data/
cp -rf ~/Github/SchoolsplayRepos/blueman/data/icons .venv3.8/lib/python3.8/site-packages/data/
find .venv3.8/lib/python3.8/site-packages/data -name "Makefile*" -exec rm  -f {} \;
find .venv3.8/lib/python3.8/site-packages/data -type d -name "build" -exec rm -rf {} \;

# Now we copy all the relevant files to the release folder
if [ -d release ]; then
    rm -rf release
fi
mkdir -p release/.venv3.8/lib/python3.8/site-packages
mkdir -p release/.venv3.8/bin
mkdir -p release/.venv3.8/lib/python3.8/site-packages/data/locale
cp -rf .venv3.8/lib/python3.8/site-packages/data release/.venv3.8/lib/python3.8/site-packages/
cp -f po/nl.gmo po/es.gmo po/en_AU.gmo release/.venv3.8/lib/python3.8/site-packages/data/locale/
cp -rf .venv3.8/lib/python3.8/site-packages/blueman release/.venv3.8/lib/python3.8/site-packages/
cp -rf .venv3.8/lib/python3.8/site-packages/cairo release/.venv3.8/lib/python3.8/site-packages/
cp -rf .venv3.8/lib/python3.8/site-packages/gi release/.venv3.8/lib/python3.8/site-packages
cp -rf .venv3.8/lib/python3.8/site-packages/pygtkcompat release/.venv3.8/lib/python3.8/site-packages/
cp -f ~/Github/SchoolsplayRepos/blueman/module/.libs/_blueman.so release/.venv3.8/lib/python3.8/site-packages/
cp -rf .venv3.8/libexec release/.venv3.8/
cp -f .venv3.8/bin/blueman-manager release/.venv3.8/bin/

tar -czf blueman-btp.tar.gz release


