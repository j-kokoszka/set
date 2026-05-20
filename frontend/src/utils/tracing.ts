import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { Resource } from '@opentelemetry/resources';
import { SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import { ZoneContextManager } from '@opentelemetry/context-zone';

const otlpEndpoint = import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT;
const otlpHeaders = import.meta.env.VITE_OTEL_EXPORTER_OTLP_HEADERS;

if (otlpEndpoint) {
  const provider = new WebTracerProvider({
    resource: new Resource({
      [SERVICE_NAME]: 'set-frontend',
    }),
  });

  const exporter = new OTLPTraceExporter({
    url: `${otlpEndpoint}/v1/traces`,
    headers: otlpHeaders ? JSON.parse(otlpHeaders) : {},
  });

  provider.addSpanProcessor(new BatchSpanProcessor(exporter));

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  registerInstrumentations({
    instrumentations: [
      getWebAutoInstrumentations({
        // load custom configuration for instrumentations if needed
        '@opentelemetry/instrumentation-fetch': {
          propagateTraceHeaderCorsUrls: [
            /.*\.kokoszka\.cloud.*/,
            /localhost.*/,
          ],
        },
      }),
    ],
  });

  console.log('OpenTelemetry initialized');
}
