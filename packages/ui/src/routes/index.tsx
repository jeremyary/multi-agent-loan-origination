import { createFileRoute } from '@tanstack/react-router';
import { Hero } from '../components/hero/hero';
import { StatusPanel } from '../components/status-panel/status-panel';
import { Footer } from '../components/footer/footer';
import { useHealth } from '../hooks/health';
import { Monitor, Server, Database } from 'lucide-react';
import type { Service } from '../schemas/health';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute('/' as any)({
  component: Index,
});

function Index() {
  // Footer is imported for consistency but rendered in root route
  void Footer;
  const { data: healthData } = useHealth();
  const services = [
    {
      id: 'ui',
      name: 'UI',
      description: 'Frontend application interface.',
      icon: <Monitor />,
      status: healthData?.find((s: Service) => s.name === 'UI')?.status || 'unknown',
      region: 'us-east-1',
      lastCheck: new Date(),
    },
    {
          id: 'api',
          name: 'API Service',
          description: 'Handles all API requests and business logic.',
          icon: <Server />,
          status: healthData?.find((s: Service) => s.name === 'API')?.status || 'unknown',
          region: 'us-east-1',
          lastCheck: new Date(),
        },
    {
          id: 'db',
          name: 'Database',
          description: 'Stores and retrieves all application data.',
          icon: <Database />,
          status: healthData?.find((s: Service) => s.name === 'Database')?.status || 'unknown',
          region: 'us-east-1',
          lastCheck: new Date(),
        },
  ];
  
  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl">
        <Hero />
        <div className="mt-6">
          <StatusPanel services={services} />
        </div>
      </div>
    </div>
  );
}