import { ServiceCard } from "../service-card/service-card";
import { useHealth } from "../../hooks/health";
import type { Service } from "../../schemas/health";

export function ServiceList() {
  const { data: services, isLoading, error } = useHealth();
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {services?.map((svc: Service) => (
        <ServiceCard key={svc.name} service={svc} isLoading={isLoading} error={error} />
      )) || []}
    </div>
  );
}