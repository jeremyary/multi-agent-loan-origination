// This project was developed with assistance from AI tools.

import { useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchDisclosureStatus } from '@/services/disclosures';

export function useDisclosures(applicationId: number | undefined) {
    const queryKey = useMemo(() => ['applications', applicationId, 'disclosures'] as const, [applicationId]);
    const queryClient = useQueryClient();

    useEffect(() => {
        const handler = () => queryClient.invalidateQueries({ queryKey });
        window.addEventListener('chat-done', handler);
        return () => window.removeEventListener('chat-done', handler);
    }, [queryClient, queryKey]);

    return useQuery({
        queryKey,
        queryFn: () => fetchDisclosureStatus(applicationId!),
        enabled: applicationId != null,
    });
}
