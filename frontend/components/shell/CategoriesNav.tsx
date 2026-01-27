import Link from "next/link";

const categories = [
  { key: "all", label: "All", href: "/products" },
  { key: "cat_1", label: "Category 1", href: "/products?category=cat_1" },
  { key: "cat_2", label: "Category 2", href: "/products?category=cat_2" },
];

export default function CategoriesNav() {
  return (
    <nav className="hidden md:flex items-center gap-3 text-sm text-muted-foreground">
      {categories.map((c) => (
        <Link key={c.key} href={c.href} className="hover:text-foreground">
          {c.label}
        </Link>
      ))}
    </nav>
  );
}
