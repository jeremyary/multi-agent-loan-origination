
import { z } from 'zod';

export const ServiceSchema = z.object({
  name: z.string(),
  status: z.enum(['healthy', 'degraded', 'down', 'unknown']),
  message: z.string(),
  version: z.string(),
  start_time: z.string(),
});

export const HealthSchema = z.array(ServiceSchema);

export type Service = z.infer<typeof ServiceSchema>;
export type Health = z.infer<typeof HealthSchema>;
