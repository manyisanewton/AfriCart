import { Swiper, SwiperSlide } from "swiper/react";
import { Autoplay, Pagination } from "swiper/modules";
import { useNavigate } from "react-router-dom";

import "swiper/css";
import "swiper/css/pagination";
import "../../styles/hero.css";

import smartTech from "../../assets/hero/smart-tech.jpg";
import kitchenPro from "../../assets/hero/kitchen-pro.jpg";
import accessories from "../../assets/hero/accessories.jpg";
import businessPro from "../../assets/hero/business-pro.jpg";
import viewzone from "../../assets/hero/viewzone.jpg";
import homeDepot from "../../assets/hero/home-depot.jpg";

const slides = [
  { img: smartTech, alt: "Smart Tech - Premium Electronics", category: "electronics" },
  { img: kitchenPro, alt: "Kitchen Pro - Smart Appliances", category: "kitchen" },
  { img: accessories, alt: "Smart Accessories", category: "accessories" },
  { img: businessPro, alt: "Business Pro - Smart Office", category: "business" },
  { img: viewzone, alt: "ViewZone - TVs & Entertainment", category: "tv-entertainment" },
  { img: homeDepot, alt: "Home Depot - Home Appliances", category: "home-appliances" },
];

export default function HeroBanner() {
  const navigate = useNavigate();

  return (
    <div className="hero-wrapper">
      <Swiper
        modules={[Autoplay, Pagination]}
        autoplay={{ delay: 2000, disableOnInteraction: false }}
        loop={true}
        pagination={{ clickable: true }}
        speed={800}
      >
        {slides.map((slide, index) => (
          <SwiperSlide key={index}>
            <div
              className="hero-slide"
              onClick={() => navigate(`/products?category=${slide.category}`)}
              style={{ cursor: "pointer" }}
            >
              <img
                src={slide.img}
                alt={slide.alt}
                className="hero-banner-img"
              />
            </div>
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
}