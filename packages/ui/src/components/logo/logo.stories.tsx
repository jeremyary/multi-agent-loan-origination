import type { Meta, StoryObj } from '@storybook/react';
import { Logo } from './logo';

const meta: Meta<typeof Logo> = {
  title: 'Components/Logo',
  component: Logo,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithText: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <Logo />
      <div>
        <h2 className="text-lg font-semibold">Your Project</h2>
        <p className="text-sm text-muted-foreground">Modern full-stack application</p>
      </div>
    </div>
  ),
};

export const InNavigation: Story = {
  render: () => (
    <nav className="flex items-center justify-between p-4 border-b">
      <Logo />
      <div className="flex gap-2">
        <button className="px-3 py-1 text-sm rounded hover:bg-accent">Home</button>
        <button className="px-3 py-1 text-sm rounded hover:bg-accent">About</button>
        <button className="px-3 py-1 text-sm rounded hover:bg-accent">Contact</button>
      </div>
    </nav>
  ),
};