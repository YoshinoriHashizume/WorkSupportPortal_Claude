#!/bin/sh
set -e
cd /app
prisma db push
exec node server.js
