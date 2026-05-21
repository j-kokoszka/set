import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { MeterProvider, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { Resource } from '@opentelemetry/resources';
import { ZoneContextManager } from '@opentelemetry/context-zone';

const otlpEndpoint = import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT;
const otlpHeaders = import.meta.env.VITE_OTEL_EXPORTER_OTLP_HEADERS;

if (otlpEndpoint) {
  const resource = new Resource({
    'service.name': 'set-frontend',
  });

  let parsedHeaders = {};
  if (otlpHeaders) {
    try {
      parsedHeaders = JSON.parse(otlpHeaders);
    } catch (e) {
      console.error('Failed to parse OTLP headers', e);
    }
  }

  // 1. Tracing Setup
  const tracerProvider = new WebTracerProvider({ resource });
  const traceExporter = new OTLPTraceExporter({
    url: `${otlpEndpoint}/v1/traces`,
    headers: parsedHeaders,
  });
  tracerProvider.addSpanProcessor(new BatchSpanProcessor(traceExporter));
  tracerProvider.register({
    contextManager: new ZoneContextManager(),
  });

  // 2. Metrics Setup
  const meterProvider = new MeterProvider({ resource });
  const metricExporter = new OTLPMetricExporter({
    url: `${otlpEndpoint}/v1/metrics`,
    headers: parsedHeaders,
  });
  meterProvider.addMetricReader(new PeriodicExportingMetricReader({
    exporter: metricExporter,
    exportIntervalMillis: 30000,
  }));

  // 3. Auto-instrumentation
  registerInstrumentations({
    instrumentations: [
      getWebAutoInstrumentations({
        '@opentelemetry/instrumentation-fetch': {
          propagateTraceHeaderCorsUrls: [
            /.*\.kokoszka\.cloud.*/,
            /localhost.*/,
          ],
        },
      }),
    ],
  });

  console.log('OpenTelemetry (Traces & Metrics) initialized');
}
