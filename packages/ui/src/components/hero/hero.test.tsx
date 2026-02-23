import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Hero } from './hero';

describe('Hero', () => {
  it('renders the welcome message', () => {
    render(<Hero />);
    expect(screen.getByText(/Welcome to/i)).toBeInTheDocument();
  });

  it('renders the template name', () => {
    render(<Hero />);
    expect(screen.getByText(/AI QuickStart Template/i)).toBeInTheDocument();
  });
});
