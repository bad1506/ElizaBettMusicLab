import type { AnchorHTMLAttributes, CSSProperties } from "react";
import { WandSparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export type GlassmorphismCtaProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  label?: string;
  avatarSrc?: string;
  avatarAlt?: string;
  spread?: string;
  shimmerColor?: string;
  speed?: string;
};

export default function GlassmorphismCta({
  label = "SØNA",
  avatarSrc = "https://images.unsplash.com/photo-1511379938547-c1f69419868d?auto=format&fit=crop&w=96&q=80",
  avatarAlt = "SØNA music interface",
  spread = "90deg",
  shimmerColor = "rgba(255,255,255,0.72)",
  speed = "4s",
  className,
  href = "#",
  onClick,
  ...props
}: GlassmorphismCtaProps) {
  return (
    <a
      href={href}
      onClick={(event) => {
        if (href === "#") event.preventDefault();
        onClick?.(event);
      }}
      className={cn(
        "group isolate inline-flex cursor-pointer overflow-hidden rounded-full relative shadow-[0_8px_40px_rgba(129,140,248,0.25)] transition-[transform,box-shadow,filter] duration-300 ease-out hover:scale-[1.03] hover:shadow-[0_0_40px_8px_rgba(129,140,248,0.35)] active:scale-[0.97]",
        className,
      )}
      style={
        {
          "--spread": spread,
          "--shimmer-color": shimmerColor,
          "--radius": "9999px",
          "--speed": speed,
          "--cut": "1px",
          "--bg": "rgba(255, 255, 255, 0.08)",
        } as CSSProperties
      }
      {...props}
    >
      <div className="absolute inset-0">
        <div className="absolute inset-[-200%] h-[400%] w-[400%] [animation:rotate-gradient_var(--speed)_linear_infinite]">
          <div className="absolute inset-0 [background:conic-gradient(from_calc(270deg-(var(--spread)*0.5)),transparent_0,var(--shimmer-color)_var(--spread),transparent_var(--spread))]" />
        </div>
      </div>
      <div className="absolute inset-[1px] rounded-full bg-white/10 backdrop-blur-xl" />
      <div className="relative z-10 flex w-full items-center gap-3 overflow-hidden px-4 py-3 text-base font-medium text-white sm:w-auto">
        <div
          className="absolute left-1/2 top-1/2 h-[200%] w-[200%]"
          style={{
            background:
              "linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)",
            animation: "borderBeamRotation 4s infinite linear",
            transform: "translate(-50%, -50%)",
          }}
        />
        <div className="absolute inset-[1px] rounded-full bg-[#0a0b14]/80 backdrop-blur-lg" />
        <img
          src={avatarSrc}
          alt={avatarAlt}
          className="relative z-10 h-8 w-8 rounded-full object-cover ring-2 ring-white/10"
        />
        <span className="relative z-10 whitespace-nowrap font-sans">{label}</span>
        <span className="relative z-10 ml-1 inline-flex h-7 w-7 items-center justify-center rounded-full bg-white/10">
          <WandSparkles className="h-4 w-5 text-white" strokeWidth={1.5} />
        </span>
      </div>
    </a>
  );
}
