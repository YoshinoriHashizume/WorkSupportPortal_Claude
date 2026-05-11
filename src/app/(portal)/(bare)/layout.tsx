export default function GonenKukumiBareLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-[1600px]">{children}</div>
    </div>
  );
}
