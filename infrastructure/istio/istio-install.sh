#!/bin/bash

# Install Istio service mesh for HealthFlow

echo "Installing Istio..."

# Download Istio
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.0 sh -
cd istio-1.20.0
export PATH=$PWD/bin:$PATH

# Install Istio with production profile
istioctl install --set profile=production -y

# Enable sidecar injection for healthflow namespace
kubectl label namespace healthflow istio-injection=enabled

# Verify installation
kubectl get pods -n istio-system

echo "Istio installed successfully!"

