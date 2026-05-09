import { DraftStudio } from "./draft-studio";

export const metadata = { title: "Draft" };

export default function DraftPage() {
  return (
    <>
      <header className="flex flex-col gap-1">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          New draft
        </h1>
        <p className="text-sm text-muted-foreground">
          Atlas writes 3 variants in your voice, tuned to your audience. Pick one,
          schedule it, approve it.
        </p>
      </header>
      <DraftStudio />
    </>
  );
}
