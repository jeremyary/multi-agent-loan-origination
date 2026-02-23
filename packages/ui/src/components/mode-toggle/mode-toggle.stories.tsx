import type { Meta, StoryObj } from '@storybook/react';
import { ModeToggle } from './mode-toggle';
import { ThemeProvider } from '../theme-provider/theme-provider';

const meta: Meta<typeof ModeToggle> = {
  title: 'Components/ModeToggle',
  component: ModeToggle,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <ThemeProvider>
        <Story />
      </ThemeProvider>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const InHeader: Story = {
  render: () => (
    <div className="flex items-center justify-between p-4 border rounded-lg">
      <span className="text-sm font-medium">Theme Settings</span>
      <ModeToggle />
    </div>
  ),
};