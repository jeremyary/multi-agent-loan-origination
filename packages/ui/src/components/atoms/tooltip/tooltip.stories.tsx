import type { Meta, StoryObj } from '@storybook/react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './tooltip';
import { Button } from '../button/button';

const meta: Meta<typeof Tooltip> = {
  title: 'Atoms/Tooltip',
  component: Tooltip,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <TooltipProvider>
        <Story />
      </TooltipProvider>
    ),
  ],
  argTypes: {
    children: {
      control: false,
      description: 'The trigger and content of the tooltip.',
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant="outline">Hover me</Button>
      </TooltipTrigger>
      <TooltipContent>
        <p>This is a tooltip</p>
      </TooltipContent>
    </Tooltip>
  ),
};

export const InFormField: Story = {
  render: () => (
    <div className="space-y-2">
      <label className="text-sm font-medium inline-flex items-center gap-2">
        Password
        <Tooltip>
          <TooltipTrigger asChild>
            <Button size="icon" variant="ghost" className="h-6 w-6">?</Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Use at least 8 characters</p>
          </TooltipContent>
        </Tooltip>
      </label>
      <input className="border rounded-md px-3 py-2 w-64 bg-background" placeholder="••••••••" />
    </div>
  ),
};