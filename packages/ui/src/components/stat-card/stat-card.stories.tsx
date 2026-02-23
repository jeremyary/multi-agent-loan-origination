import type { Meta, StoryObj } from '@storybook/react';
import { StatCard } from './stat-card';

const meta: Meta<typeof StatCard> = {
  title: 'Components/StatCard',
  component: StatCard,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    label: { control: 'text' },
    value: { control: 'text' },
    tone: {
      control: {
        type: 'select',
        options: ['emerald', 'sky', 'violet'],
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    label: 'Label',
    value: 'Value',
    tone: 'emerald',
  },
};

export const AllTones: Story = {
  render: () => (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <StatCard label="Emerald" value="42" tone="emerald" />
      <StatCard label="Sky" value="99" tone="sky" />
      <StatCard label="Violet" value="12" tone="violet" />
    </div>
  ),
};