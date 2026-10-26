#!/bin/bash
set -e
UV=/root/nodebuild/node-v24.22.1/deps/npm
STAGE=/root/nodebuild/stage
rm -rf $STAGE
mkdir -p $STAGE/bin $STAGE/lib/node_modules
echo "=== npm subtree sizes ==="
du -sh $UV/* 2>/dev/null | sort -h | tail -8
cp -a $UV $STAGE/lib/node_modules/npm
# tests/docs are not needed at runtime; keep them out to shrink the upload
rm -rf $STAGE/lib/node_modules/npm/test $STAGE/lib/node_modules/npm/tap-snapshots

cat > $STAGE/bin/node <<'EOF'
#!/bin/sh
LD_LIBRARY_PATH=/var/tmp/nodedist/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH
exec /var/tmp/nodedist/bin/node.bin "$@"
EOF

cat > $STAGE/bin/npm <<'EOF'
#!/bin/sh
LD_LIBRARY_PATH=/var/tmp/nodedist/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH
: ${npm_config_cache:=/var/tmp/nodedist/.npm-cache}
export npm_config_cache
exec /var/tmp/nodedist/bin/node.bin /var/tmp/nodedist/lib/node_modules/npm/bin/npm-cli.js "$@"
EOF

cat > $STAGE/bin/npx <<'EOF'
#!/bin/sh
LD_LIBRARY_PATH=/var/tmp/nodedist/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH
: ${npm_config_cache:=/var/tmp/nodedist/.npm-cache}
export npm_config_cache
exec /var/tmp/nodedist/bin/node.bin /var/tmp/nodedist/lib/node_modules/npm/bin/npx-cli.js "$@"
EOF
chmod +x $STAGE/bin/node $STAGE/bin/npm $STAGE/bin/npx

echo "=== stage size ==="
du -sh $STAGE
rm -f /root/nodebuild/npm-stage.tar
tar -C $STAGE -cf /root/nodebuild/npm-stage.tar bin lib/node_modules
ls -l /root/nodebuild/npm-stage.tar
cp -f /root/nodebuild/npm-stage.tar /mnt/d/BB10/wslbuild/deploy/npm-stage.tar
echo "=== tar contents (top) ==="
tar -tf /root/nodebuild/npm-stage.tar | head -10
