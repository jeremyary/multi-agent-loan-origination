import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './button';
import { Plus, Download, ArrowRight, Settings } from 'lucide-react';

const meta: Meta<typeof Button> = {
  title: 'Atoms/Button',
  component: Button,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: {
        type: 'select',
        options: ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'],
      },
      description: 'The variant of the button.',
    },
    size: {
      control: {
        type: 'select',
        options: ['default', 'sm', 'lg', 'icon'],
      },
      description: 'The size of the button.',
    },
    children: {
      control: 'text',
      description: 'The content of the button.',
    },
    asChild: {
      control: 'boolean',
      description: 'Render as a child component.',
    },
    disabled: {
      control: 'boolean',
      description: 'Whether the button is disabled.',
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    variant: 'default',
    size: 'default',
    children: 'Button',
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <Button variant="default">Default</Button>
        <Button variant="destructive">Destructive</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="link">Link</Button>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="default" disabled>Default</Button>
        <Button variant="destructive" disabled>Destructive</Button>
        <Button variant="outline" disabled>Outline</Button>
        <Button variant="secondary" disabled>Secondary</Button>
        <Button variant="ghost" disabled>Ghost</Button>
        <Button variant="link" disabled>Link</Button>
      </div>
    </div>
  ),
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-center gap-2">
      <Button variant="default" size="sm">Small</Button>
      <Button variant="default" size="default">Default</Button>
      <Button variant="default" size="lg">Large</Button>
      <Button variant="default" size="icon">
        <Settings />
      </Button>
    </div>
  ),
};

export const WithIcons: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Button>
        <Plus />
        Add Item
      </Button>
      <Button variant="outline">
        <Download />
        Download
      </Button>
      <Button variant="secondary">
        Continue
        <ArrowRight />
      </Button>
    </div>
  ),
};

export const IconOnly: Story = {
  render: () => (
    <div className="flex gap-2">
      <Button variant="default" size="icon">
        <Plus />
      </Button>
      <Button variant="outline" size="icon">
        <Download />
      </Button>
      <Button variant="ghost" size="icon">
        <Settings />
      </Button>
    </div>
  ),
};

export const Loading: Story = {
  render: () => (
    <div className="flex gap-2">
      <Button disabled>
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-foreground" />
        Loading...
      </Button>
      <Button variant="outline" disabled>
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
        Please wait
      </Button>
    </div>
  ),
};