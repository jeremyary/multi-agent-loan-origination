// This project was developed with assistance from AI tools.
export default {
    "packages/ui/**/*.{js,jsx,ts,tsx,css,md,html,json}": (files) => [
        `pnpm --filter ui prettier --write -- ${files.join(" ")}`,
        `pnpm --filter ui eslint --max-warnings 0 -- ${files.join(" ")}`,
    ],
    "packages/api/**/*.py": (files) => [
        `uv run --directory packages/api ruff format --respect-gitignore -- ${files.join(" ")}`,
        `uv run --directory packages/api ruff check -- ${files.join(" ")}`,
    ],
};
