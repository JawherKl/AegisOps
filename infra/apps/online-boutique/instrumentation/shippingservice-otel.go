package main

import (
	"context"
	"net/url"
	"os"
	"strings"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	sdkresource "go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func initTracing() func() {
	if os.Getenv("DISABLE_TRACING") != "" {
		return func() {}
	}

	ctx := context.Background()
	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = os.Getenv("COLLECTOR_SERVICE_ADDR")
	}
	if endpoint == "" {
		log.Fatal("OTEL exporter endpoint is required when tracing is enabled")
	}

	exporterOptions := []otlptracegrpc.Option{}
	if strings.Contains(endpoint, "://") {
		parsed, err := url.Parse(endpoint)
		if err != nil || parsed.Host == "" {
			log.Fatalf("invalid OTEL exporter endpoint %q", endpoint)
		}
		switch parsed.Scheme {
		case "http":
			exporterOptions = append(exporterOptions, otlptracegrpc.WithEndpoint(parsed.Host), otlptracegrpc.WithInsecure())
		case "https":
			exporterOptions = append(exporterOptions, otlptracegrpc.WithEndpoint(parsed.Host))
		default:
			log.Fatalf("unsupported OTEL exporter endpoint scheme %q", parsed.Scheme)
		}
	} else {
		exporterOptions = append(exporterOptions, otlptracegrpc.WithEndpoint(endpoint), otlptracegrpc.WithInsecure())
	}

	exporter, err := otlptracegrpc.New(ctx, exporterOptions...)
	if err != nil {
		log.Fatalf("create OTLP trace exporter: %v", err)
	}
	res := sdkresource.NewWithAttributes(
		"",
		attribute.String("service.name", "shippingservice"),
		attribute.String("service.namespace", "online-boutique"),
		attribute.String("deployment.environment", "testbed"),
	)
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	return func() {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := provider.Shutdown(shutdownCtx); err != nil {
			log.Errorf("shut down OTEL trace provider: %v", err)
		}
	}
}
