#!/bin/bash

helm upgrade --install cnpg --namespace apps cnpg/cloudnative-pg -f k8s/deps/cnpg-values.yaml
helm upgrade --install traefik traefik/traefik -f k8s/deps/traefik-values.yaml --namespace=default --atomic --cleanup-on-fail --debug
helm upgrade --install centrifugo centrifugal/centrifugo -f k8s/deps/centrifugo-values.yaml --namespace=apps --atomic --cleanup-on-fail --debug
helm upgrade --install --force keydb enapter/keydb -f k8s/deps/keydb-values.yaml --namespace=apps --atomic --cleanup-on-fail --debug

kubectl apply -f k8s/deps/pg-cluster.yaml
