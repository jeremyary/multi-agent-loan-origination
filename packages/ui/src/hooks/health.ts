
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { useMemo } from 'react';
import { getHealth } from '../services/health';
import type { Health, Service } from '../schemas/health';

// Track UI start time (when the hook first runs)
const UI_START_TIME = new Date().toISOString();

export const useHealth = (): UseQueryResult<Health, Error> => {
  const queryResult = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  });

  // Add UI service to the list of services
  const enhancedData = useMemo((): Health | undefined => {
    if (!queryResult.data) {
      return queryResult.data;
    }

    // Check if UI service already exists (shouldn't happen, but be safe)
    const hasUIService = queryResult.data.some((service: Service) => service.name === 'UI');

    if (hasUIService) {
      return queryResult.data;
    }

    // Add UI service entry - ensure it matches Service type
    const uiService: Service = {
      name: 'UI',
      status: 'healthy',
      message: 'Frontend application is running',
      version: '0.0.0',
      start_time: UI_START_TIME,
    };

    return [...queryResult.data, uiService];
  }, [queryResult.data]);

  // Return query result with enhanced data using Object.assign to avoid type inference issues
  return Object.assign({}, queryResult, { data: enhancedData }) as UseQueryResult<Health, Error>;
};
