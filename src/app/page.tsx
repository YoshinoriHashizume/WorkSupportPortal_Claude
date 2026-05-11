import { redirect } from "next/navigation";
import { redirectIfAuthenticated } from "@/app/_lib/server-auth";

export default async function Home() {
  await redirectIfAuthenticated("/dashboard");
  redirect("/login");
}
