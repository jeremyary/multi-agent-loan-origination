import type { Meta, StoryObj } from '@storybook/react';
import { ServiceCard } from './service-card';
import type { Service } from '../../schemas/health';

const meta: Meta<typeof ServiceCard> = {
  title: 'Components/ServiceCard',
  component: ServiceCard,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Healthy: Story = {
  args: {
    service: {
      name: 'Database',
      status: 'healthy',
      message: 'Primary database',
      version: '0.0.0',
      start_time: new Date().toISOString(),
    } as Service,
    isLoading: false,
  },
};

export const AllStatuses: Story = {
  render: () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
      <ServiceCard
        service={{
          name: 'Database',
          status: 'healthy',
          message: 'Primary PostgreSQL database',
          version: '0.0.0',
          start_time: new Date().toISOString(),
        } as Service}
        isLoading={false}
      />
      <ServiceCard
        service={{
          name: 'API Gateway',
          status: 'degraded',
          message: 'Main API endpoint',
          version: '0.0.0',
          start_time: new Date(Date.now() - 60000).toISOString(),
        } as Service}
        isLoading={false}
      />
      <ServiceCard
        service={{
          name: 'CDN',
          status: 'down',
          message: 'Content delivery network',
          version: '0.0.0',
          start_time: new Date(Date.now() - 300000).toISOString(),
        } as Service}
        isLoading={false}
      />
      <ServiceCard
        service={{
          name: 'Auth Service',
          status: 'healthy',
          message: 'User authentication',
          version: '0.0.0',
          start_time: new Date(Date.now() - 30000).toISOString(),
        } as Service}
        isLoading={false}
      />
    </div>
  ),
};

export const Loading: Story = {
  args: {
    service: {
      name: 'Loading Service',
      status: 'healthy',
      message: 'Checking status...',
      version: '0.0.0',
      start_time: new Date().toISOString(),
    } as Service,
    isLoading: true,
  },
};