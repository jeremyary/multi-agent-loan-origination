import { CircleHelp } from "lucide-react";
import { ServiceList } from "../service-list/service-list";

type Service = {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  status: "healthy" | "degraded" | "down" | "unknown";
  region?: string;
  endpoint?: string;
  port?: number;
  lastCheck?: Date;
  error?: string;
};

export function StatusPanel({ services }: { services: Service[] }) {
  if (services.length === 0) {
    return (
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Services</h2>
        <p className="text-sm text-muted-foreground">No services configured</p>
        <div className="text-center py-8">
          <CircleHelp className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">
            Add packages like API or Database to see services here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-2xl font-semibold tracking-tight">Services</h2>
        <p className="text-sm text-muted-foreground">
          Explore each package to get started
        </p>
      </div>
      <ServiceList />
    </div>
  );
}