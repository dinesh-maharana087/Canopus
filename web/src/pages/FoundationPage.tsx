type FoundationPageProps = {
  title: string;
};

export function FoundationPage({ title }: FoundationPageProps) {
  return (
    <main className="foundation-page">
      <h1>{title}</h1>
      <p>Not implemented in Stage 1</p>
    </main>
  );
}
