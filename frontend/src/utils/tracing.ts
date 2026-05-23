import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { MeterProvider, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { ZoneContextManager } from '@opentelemetry/context-zone';

const otlpEndpoint = import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT;
const otlpHeaders = import.meta.env.VITE_OTEL_EXPORTER_OTLP_HEADERS;

if (otlpEndpoint) {
  const resource = resourceFromAttributes({
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
  const traceExporter = new OTLPTraceExporter({
    url: `${otlpEndpoint}/v1/traces`,
    headers: parsedHeaders,
  });
  const tracerProvider = new WebTracerProvider({ 
    resource,
    spanProcessors: [new BatchSpanProcessor(traceExporter)]
  });
  tracerProvider.register({
    contextManager: new ZoneContextManager(),
  });

  // 2. Metrics Setup
  const metricExporter = new OTLPMetricExporter({
    url: `${otlpEndpoint}/v1/metrics`,
    headers: parsedHeaders,
  });
  new MeterProvider({ 
    resource,
    readers: [
      new PeriodicExportingMetricReader({
        exporter: metricExporter,
        exportIntervalMillis: 30000,
      })
    ]
  });

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
