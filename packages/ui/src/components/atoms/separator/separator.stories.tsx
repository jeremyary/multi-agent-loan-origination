import type { Meta, StoryObj } from '@storybook/react';
import { Separator } from './separator';

const meta: Meta<typeof Separator> = {
  title: 'Atoms/Separator',
  component: Separator,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    orientation: {
      control: {
        type: 'select',
        options: ['horizontal', 'vertical'],
      },
      description: 'The orientation of the separator.',
    },
    decorative: {
      control: 'boolean',
      description: 'Whether the separator is decorative.',
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Horizontal: Story = {
  render: (args) => (
    <div className="w-40">
      <Separator {...args} />
    </div>
  ),
  args: {
    orientation: 'horizontal',
  },
};

export const Vertical: Story = {
  render: (args) => (
    <div className="h-20">
      <Separator {...args} />
    </div>
  ),
  args: {
    orientation: 'vertical',
  },
};

export const InCard: Story = {
  render: (args) => (
    <div className="w-64 border rounded-lg bg-card p-3 space-y-3">
      <div className="text-sm">Section A</div>
      <Separator {...args} />
      <div className="text-sm">Section B</div>
    </div>
  ),
  args: {
    orientation: 'horizontal',
  },
};