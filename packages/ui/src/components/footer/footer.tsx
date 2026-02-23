import { Logo } from "../logo/logo";

export function Footer() {
  return (
    <footer className="w-full border-t bg-background">
      <div className="container mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 text-xs text-muted-foreground sm:px-6 lg:px-8">
        <div className="flex items-center gap-0">
          <Logo />
          <span className="font-medium text-foreground">
            Built with the <span className="font-bold">AI QuickStart Template</span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground">·</span>
          <a className="hover:underline" href="https://github.com/rh-ai-quickstart/ai-quickstart-template" target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}