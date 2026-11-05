import sqlite3
import json
import random

DB_FILE = "homestay.db"

# Chuỗi Homestay thương hiệu "EkkoStay Chain" (Cùng 1 chủ sở hữu)
CHAIN_NAME = "EkkoStay"

# Chính sách chung của chuỗi áp dụng cho tất cả các căn
COMMON_POLICIES = [
    (
        "checkin_checkout",
        "Giờ nhận và trả phòng tiêu chuẩn",
        "Giờ check-in: từ 14:00. Giờ check-out: trước 12:00 trưa. Khách có nhu cầu check-in sớm hoặc check-out muộn vui lòng liên hệ trước, nếu còn phòng trống chuỗi sẽ hỗ trợ với phụ phí 50.000 VNĐ/giờ."
    ),
    (
        "cancellation",
        "Chính sách đặt cọc và huỷ phòng",
        "Để giữ phòng, quý khách cần đặt cọc 50% tổng tiền. Huỷ trước 5 ngày nhận phòng được hoàn 100% tiền cọc. Huỷ từ 2-5 ngày hoàn lại 50% tiền cọc. Huỷ trong vòng 48 giờ trước giờ nhận phòng không hỗ trợ hoàn cọc."
    ),
    (
        "pets",
        "Quy định mang thú cưng",
        "Chuỗi EkkoStay có các căn thân thiện với thú cưng (có gắn nhãn 'Cho phép thú cưng'). Áp dụng cho cún/mèo dưới 10kg, phụ phí vệ sinh 100.000 VNĐ/bé/đêm. Vui lòng mang tã/bỉm cho thú cưng và không để thú cưng nằm trực tiếp lên giường nệm hoặc xuống hồ bơi."
    ),
    (
        "quiet_hours",
        "Quy định giữ gìn trật tự và yên tĩnh",
        "Khung giờ yên tĩnh từ 22:30 đến 07:00 sáng hôm sau. Nghiêm cấm sử dụng loa kéo công suất lớn, bay lắc, tàng trữ chất cấm hoặc các hành vi vi phạm pháp luật."
    ),
    (
        "bbq",
        "Chính sách sử dụng bếp nướng BBQ",
        "Đối với các căn có sân BBQ, chuỗi trang bị sẵn bếp than và vỉ nướng. Phí dịch vụ hỗ trợ than nướng, cồn mồi và dọn rửa tro bếp sau tiệc là 120.000 VNĐ/lần sử dụng."
    ),
    (
        "children_and_extra_guests",
        "Chính sách trẻ em và phát sinh thêm người",
        "Trẻ em dưới 6 tuổi: miễn phí tiền phòng (tối đa 2 bé/căn). Trẻ từ 6-11 tuổi hoặc người lớn phát sinh thêm ngoài sức chứa tiêu chuẩn (nếu căn còn chỗ kê nệm phụ): phụ thu 150.000 VNĐ/người/đêm (bao gồm nệm phụ và khăn tắm). Nghiêm cấm ở vượt quá số lượng tối đa niêm yết của căn để đảm bảo an toàn."
    ),
    (
        "fees_and_cleaning",
        "Chính sách phí vệ sinh và chi phí dịch vụ",
        "Giá niêm yết của EkkoStay là trọn gói 100%, đã bao gồm phí vệ sinh tiêu chuẩn khi nhận và trả phòng. Chuỗi cam kết không phát sinh bất kỳ khoản phí dọn dẹp ẩn nào. Khách chỉ thanh toán thêm nếu có nhu cầu: than nướng BBQ (120k/lần) hoặc phụ phí thú cưng (100k/bé/đêm)."
    ),
    (
        "reschedule",
        "Chính sách đổi ngày và thay đổi đặt phòng",
        "Chuỗi hỗ trợ đổi ngày nhận phòng miễn phí 01 lần nếu khách thông báo trước ít nhất 5 ngày so với ngày nhận phòng (áp dụng nếu căn còn trống vào ngày mới). Nếu đổi ngày trước 2-5 ngày: phụ phí đổi lịch 100.000 VNĐ. Đổi ngày trong vòng 48 giờ trước giờ nhận phòng: không hỗ trợ đổi ngày, áp dụng theo chính sách huỷ cọc."
    )
]

def generate_homestays():
    homestays = []
    
    # -------------------------------------------------------------
    # 1. ĐÀ LẠT (~20 CĂN)
    # -------------------------------------------------------------
    dalat_templates = [
        # (name, district, address, landmark, max_guests, bedrooms, beds, price, bathtub, pets, kitchen, pool, bbq, amenities, desc)
        (
            "EkkoStay Mây Mù - Studio View Thung Lũng", "Phường 4", "15/3 Triệu Việt Vương, Phường 4, TP. Đà Lạt",
            "Gần Dinh 3, cách Hồ Xuân Hương 2km", 2, 1, 1, 650000, 1, 1, 1, 0, 1,
            ["Bồn tắm nằm view đồi thông", "Cho thú cưng", "Máy chiếu mini", "Bếp gia vị", "Sân BBQ nhỏ"],
            "Căn studio áp mái lãng mạn với bồn tắm kính nhìn thẳng ra thung lũng thông reo. Buổi sáng ngắm trọn biển mây tại giường."
        ),
        (
            "EkkoStay Pine Hill - Bungalow Rừng Thông", "Phường 3", "28 Đặng Thái Thân, Phường 3, TP. Đà Lạt",
            "Đầu đèo Prenn, cách Bến xe Liên Tỉnh 800m", 2, 1, 1, 550000, 0, 1, 0, 0, 1,
            ["Cho thú cưng", "Ban công ngắm rừng thông", "Sân đốt lửa trại", "Trà atiso miễn phí"],
            "Bungalow gỗ mộc mạc nép mình giữa sườn đồi thông xanh ngát, không khí mát lạnh quanh năm."
        ),
        (
            "EkkoStay Zen Villa - Hồ Bơi Nước Ấm Bốn Mùa", "Phường 8", "42 Phù Đổng Thiên Vương, Phường 8, TP. Đà Lạt",
            "Gần Thung Lũng Tình Yêu, Đại học Đà Lạt", 8, 3, 4, 2600000, 1, 0, 1, 1, 1,
            ["Hồ bơi nước ấm 32 độ", "Bồn tắm sục Jacuzzi", "Sân cỏ BBQ ngoài trời", "Chỗ đậu xe ô tô 7 chỗ", "Bếp lớn"],
            "Biệt thự phong cách Bắc Âu sang trọng, có hồ bơi bốn mùa nước ấm trong nhà và sân vườn nướng BBQ cực rộng cho nhóm bạn hoặc gia đình."
        ),
        (
            "EkkoStay Lakeside - Căn Hộ View Hồ Xuân Hương", "Phường 1", "02 Nguyễn Du, Phường 1, TP. Đà Lạt",
            "Sát Hồ Xuân Hương, cách Chợ Đêm 600m", 4, 2, 2, 1300000, 1, 0, 1, 0, 0,
            ["Bồn tắm sứ", "Đi bộ ra Hồ Xuân Hương 2 phút", "Bếp từ hiện đại", "Smart TV 55 inch"],
            "Vị trí đắc địa ngay trung tâm, bước vài bước là ra tới bờ hồ Xuân Hương và phố đi bộ chợ đêm."
        ),
        (
            "EkkoStay Hoàng Hôn - Gỗ Mộc View Đồi Robin", "Phường 3", "34 Khởi Nghĩa Bắc Sơn, Phường 3, TP. Đà Lạt",
            "Gần Cáp Treo Đồi Robin, Dinh 2", 2, 1, 1, 700000, 1, 1, 1, 0, 1,
            ["Bồn tắm gỗ thảo mộc", "Cho thú cưng", "Ban công ngắm hoàng hôn", "Bếp BBQ ngoài trời"],
            "Nơi ngắm hoàng hôn màu tím rực rỡ nhất Đà Lạt. Bồn tắm thảo mộc giúp bạn thư giãn sau ngày dài dạo phố."
        ),
        (
            "EkkoStay Family Garden - Căn Hộ Sân Vườn", "Phường 10", "18 Hùng Vương, Phường 10, TP. Đà Lạt",
            "Gần Ga Đà Lạt, Trường Cao Đẳng Sư Phạm", 6, 2, 3, 1400000, 0, 1, 1, 0, 1,
            ["Cho thú cưng", "Sân vườn hoa cẩm tú cầu", "Bếp nướng BBQ ngoài trời", "Bếp nấu gia đình"],
            "Căn hộ tầng trệt có sân vườn riêng nở đầy hoa cẩm tú cầu, rất thoáng đãng cho trẻ nhỏ và thú cưng chạy nhảy."
        ),
        (
            "EkkoStay Cloud Nine - Loft Áp Mái Kính", "Phường 5", "56 Hoàng Diệu, Phường 5, TP. Đà Lạt",
            "Khu ẩm thực bánh căn Nhà Chung, cách Chợ Đêm 1km", 2, 1, 1, 600000, 1, 0, 0, 0, 0,
            ["Bồn tắm tròn view bầu trời", "Cửa sổ trần ngắm sao", "Máy sưởi ấm", "Gần chợ ẩm thực"],
            "Thiết kế trần kính trong suốt độc đáo cho phép bạn ngắm trăng sao ngay trên giường ngủ giữa tiết trời se lạnh."
        ),
        (
            "EkkoStay Thảo Mộc - Căn Nhà Gỗ Mộc Mạc", "Phường 4", "89 An Bình, Phường 4, TP. Đà Lạt",
            "Gần Dinh 3, Hồ Tuyền Lâm 3km", 4, 2, 2, 900000, 0, 1, 1, 0, 1,
            ["Cho thú cưng", "Bếp củi & BBQ", "Vườn rau sạch tự hái", "Không gian yên tĩnh tuyệt đối"],
            "Ngôi nhà nhỏ nằm giữa vườn rau và dâu tây hữu cơ, được phép tự tay hái rau tươi nấu ăn."
        ),
        (
            "EkkoStay Forest Retreat - Villa Ven Hồ Tuyền Lâm", "Phường 4", "Khu Tuyền Lâm, Phường 4, TP. Đà Lạt",
            "Sát Hồ Tuyền Lâm, gần Thiền Viện Trúc Lâm", 10, 4, 5, 3500000, 1, 1, 1, 1, 1,
            ["Hồ bơi tràn viền view hồ nước", "Bồn tắm ngoài trời", "Bến thuyền kayak riêng", "Sân BBQ 100m2", "Cho thú cưng"],
            "Villa nghỉ dưỡng cao cấp chuẩn 5 sao biệt lập giữa rừng thông Tuyền Lâm, có chèo thuyền kayak và hồ bơi vô cực."
        ),
        (
            "EkkoStay Chợ Đêm - Studio Tiện Nghi", "Phường 1", "12 Nam Kỳ Khởi Nghĩa, Phường 1, TP. Đà Lạt",
            "Cách Chợ Đêm Đà Lạt 200m", 2, 1, 1, 500000, 0, 0, 0, 0, 0,
            ["Trung tâm phố đi bộ", "Thang máy", "Gần tiệm bánh Cối Xay Gió", "Thuê xe máy giá rẻ"],
            "Nằm ngay trung tâm sầm uất, chỉ cần đi bộ 3 phút tới chợ đêm, thuận tiện ăn uống và mua sắm quà lưu niệm."
        ),
        (
            "EkkoStay Đồi Chè - Nhà Kính Trại Mát", "Phường 11", "Tự Phước, Trại Mát, TP. Đà Lạt",
            "Gần Chùa Ve Chai, Đồi Chè Cầu Đất", 4, 2, 2, 850000, 1, 1, 1, 0, 1,
            ["Bồn tắm ngắm nhà lồng đom đóm", "Cho thú cưng", "View thung lũng đèn đêm", "Bếp BBQ ngoài trời"],
            "Đêm xuống cả thung lũng bừng sáng lung linh như biển đom đóm, trải nghiệm ngắm cảnh đêm Đà Lạt không thể quên."
        ),
        (
            "EkkoStay Vintage House - Phong Cách Đông Dương", "Phường 2", "14 Yersin, Phường 2, TP. Đà Lạt",
            "Gần Trường Sư Phạm, Quảng Trường Lâm Viên", 4, 2, 2, 950000, 1, 0, 1, 0, 0,
            ["Bồn tắm chân rồng cổ điển", "Nội thất gỗ xưa Indochine", "Máy pha cafe espresso", "Gần quảng trường"],
            "Căn nhà đậm chất hoài cổ Đông Dương với gạch hoa cổ điển, bồn tắm vintage và mùi hương tinh dầu quế ấm nồng."
        ),
        (
            "EkkoStay Hillside - Căn Góc View 270 Độ", "Phường 7", "23 Mai Anh Đào, Phường 7, TP. Đà Lạt",
            "Gần Đồi Mộng Mơ, Thung Lũng Tình Yêu", 2, 1, 1, 620000, 1, 1, 0, 0, 1,
            ["Bồn tắm kính", "Cho thú cưng", "View ôm trọn đồi thông", "Sân nướng BBQ"],
            "Căn góc hai mặt kính nhìn bao quát toàn bộ đồi núi phía Bắc thành phố, đón bình minh rực rỡ mỗi sớm."
        ),
        (
            "EkkoStay The Nest - Tổ Chim Rừng Rậm", "Phường 3", "05 Tô Hiến Thành, Phường 3, TP. Đà Lạt",
            "Gần Bến xe Phương Trang, Cổng Trời Bali", 2, 1, 1, 480000, 0, 1, 0, 0, 0,
            ["Cho thú cưng", "Nhiều cây xanh nhiệt đới", "Góc sống ảo check-in", "Gần quán cafe Cổng Trời"],
            "Căn phòng nhỏ xinh xắn ngập tràn hoa lá và ánh sáng tự nhiên, giá cực kỳ tiết kiệm cho học sinh sinh viên."
        ),
        (
            "EkkoStay Secret Garden - Biệt Thự Vườn Cổ Tích", "Phường 5", "101 Cam Ly, Phường 5, TP. Đà Lạt",
            "Gần Thác Cam Ly, Làng Hoa Vạn Thành", 8, 3, 4, 2300000, 1, 1, 1, 0, 1,
            ["Bồn tắm lớn", "Cho thú cưng", "Sân vườn rộng 300m2", "Khu cắm trại lều ngoài trời", "Bếp nướng BBQ"],
            "Khuôn viên vườn cổ tích với suối nhỏ nhân tạo và bãi cỏ cắm trại, phù hợp tổ chức tiệc gia đình hoặc họp lớp."
        ),
        (
            "EkkoStay Sunrise - Đỉnh Đồi Đón Bình Minh", "Phường 10", "45 Khe Sanh, Phường 10, TP. Đà Lạt",
            "Gần Chùa Tàu, đèo Mimosa", 4, 2, 2, 800000, 0, 0, 1, 0, 1,
            ["View biển mây bình minh", "Ban công panorama", "Bếp gia đình", "Sân nướng BBQ"],
            "Nằm trên cung đường đèo ngắm bình minh tuyệt đẹp, không gian mở thoáng đãng nhìn về đồi chè và thung lũng."
        ),
        (
            "EkkoStay Memory - Nhà Cổ Thời Bao Cấp", "Phường 6", "77 Hai Bà Trưng, Phường 6, TP. Đà Lạt",
            "Gần Nhà Thờ Domaine de Marie", 2, 1, 1, 520000, 0, 1, 0, 0, 0,
            ["Cho thú cưng", "Decor phong cách retro thập niên 90", "Đĩa than cassette", "Gần khu ăn uống Hai Bà Trưng"],
            "Không gian lưu giữ những kỷ niệm tuổi thơ với radio cổ, tivi đen trắng và bộ bàn ghế gỗ cũ."
        ),
        (
            "EkkoStay Panorama - Căn Hộ Tầng Cao", "Phường 9", "08 Quang Trung, Phường 9, TP. Đà Lạt",
            "Gần Ga Xe Lửa Cổ Đà Lạt", 4, 2, 2, 1100000, 1, 0, 1, 0, 0,
            ["Bồn tắm view toàn cảnh thành phố", "Thang máy", "Kính cách âm chống ồn", "Bếp từ âm"],
            "Căn hộ cao cấp với tường kính kịch trần nhìn trọn cảnh thành phố Đà Lạt mộng mơ từ trên cao."
        )
    ]
    for item in dalat_templates:
        homestays.append(("Đà Lạt", *item))

    # -------------------------------------------------------------
    # 2. TP. HỒ CHÍ MINH (~16 CĂN)
    # -------------------------------------------------------------
    hcm_templates = [
        (
            "EkkoStay Landmark View Sông - Căn Hộ Cao Cấp", "Bình Thạnh", "208 Nguyễn Hữu Cảnh, Phường 22, Bình Thạnh, TP. HCM",
            "Tòa nhà Landmark 81, Vinhomes Central Park", 4, 2, 2, 1800000, 1, 0, 1, 1, 0,
            ["Bồn tắm view sông Sài Gòn", "Hồ bơi vô cực toà nhà", "Công viên bờ sông 14ha", "Trung tâm thương mại Vincom"],
            "Căn hộ cao cấp ngay quần thể Landmark 81, tầng cao lộng gió ngắm trọn vẹn khúc sông Sài Gòn uốn lượn và pháo hoa."
        ),
        (
            "EkkoStay Saigon Retro Loft - Phố Đi Bộ", "Quận 1", "42 Nguyễn Huệ, Bến Nghé, Quận 1, TP. HCM",
            "Chung cư 42 Nguyễn Huệ, sát Phố Đi Bộ", 2, 1, 1, 950000, 1, 1, 1, 0, 0,
            ["Bồn tắm kiểu Pháp", "Cho thú cưng", "Ban công nhìn thẳng Phố Đi Bộ Nguyễn Huệ", "Nhiều quán cafe hot"],
            "Nằm ngay trong toà nhà cafe nổi tiếng bậc nhất Sài Gòn, ban công nhìn thẳng xuống phố đi bộ nhộn nhịp."
        ),
        (
            "EkkoStay Thảo Điền - Biệt Thự Hồ Bơi Xanh Mát", "Quận 2", "12 Quốc Hương, Thảo Điền, TP. Thủ Đức (Quận 2), TP. HCM",
            "Khu phố Tây Thảo Điền, gần sông Sài Gòn", 6, 3, 3, 3200000, 1, 1, 1, 1, 1,
            ["Hồ bơi riêng biệt lập", "Bồn tắm sục Jacuzzi", "Sân vườn nướng BBQ", "Cho thú cưng tự do", "Bếp chuẩn Châu Âu"],
            "Oasis xanh giữa lòng Thảo Điền náo nhiệt, hồ bơi riêng tư tuyệt đối, đầy đủ tiện nghi cao cấp chuẩn nghỉ dưỡng."
        ),
        (
            "EkkoStay Ben Thanh Central - Studio Sang Trọng", "Quận 1", "136 Lê Thánh Tôn, Bến Thành, Quận 1, TP. HCM",
            "Cách Chợ Bến Thành 100m, Ga Metro Bến Thành", 2, 1, 1, 850000, 1, 0, 1, 0, 0,
            ["Bồn tắm sứ cao cấp", "Đi bộ 1 phút tới Chợ Bến Thành", "Hệ thống khoá cửa thông minh", "Bếp từ nấu ăn"],
            "Vị trí trái tim Sài Gòn, cực kỳ tiện lợi để đi bộ ra chợ Bến Thành, bảo tàng Mỹ Thuật và các trung tâm mua sắm."
        ),
        (
            "EkkoStay Sky Pool - Căn Hộ Millennium Bến Vân Đồn", "Quận 4", "132 Bến Vân Đồn, Phường 6, Quận 4, TP. HCM",
            "Cách Quận 1 một cây cầu (Cầu Ông Lãnh)", 4, 2, 2, 1400000, 0, 1, 1, 1, 0,
            ["Hồ bơi vô cực tầng thượng view Bitexco", "Cho thú cưng", "Phòng gym miễn phí", "Nội thất cao cấp"],
            "Chỉ mất 3 phút qua cầu là đến Quận 1. Tận hưởng hồ bơi tầng thượng với tầm nhìn biểu tượng Bitexco và toà nhà tài chính."
        ),
        (
            "EkkoStay Phú Mỹ Hưng - Căn Hộ Gia Đình", "Quận 7", "Nguyễn Đức Cảnh, Tân Phong, Quận 7, TP. HCM",
            "Gần Cầu Ánh Sao, Hồ Bán Nguyệt, TTTM Crescent Mall", 6, 3, 3, 1900000, 1, 0, 1, 1, 0,
            ["Bồn tắm nằm", "Hồ bơi người lớn & trẻ em", "Gần công viên Cầu Ánh Sao", "Môi trường xanh sạch yên tĩnh"],
            "Khu đô thị kiểu mẫu thoáng đãng, nhiều cây xanh, an ninh 24/7, cực kỳ phù hợp cho kỳ nghỉ gia đình có người lớn tuổi."
        ),
        (
            "EkkoStay Bùi Viện Vibes - Studio Trẻ Trung", "Quận 1", "185 Bùi Viện, Phạm Ngũ Lão, Quận 1, TP. HCM",
            "Ngay trung tâm Phố Tây Bùi Viện", 2, 1, 1, 600000, 0, 1, 0, 0, 0,
            ["Cho thú cưng", "Cách âm tốt 2 lớp cửa", "Smart TV Netflix", "Gần các quán bar pub nổi tiếng"],
            "Dành cho những bạn trẻ yêu thích không khí sôi động, náo nhiệt về đêm của phố Tây Sài Gòn nhưng phòng vẫn cách âm yên tĩnh."
        ),
        (
            "EkkoStay Bàn Cờ - Nhà Cổ Hẻm Ẩm Thực", "Quận 3", "Hẻm 400 Nguyễn Đình Chiểu, Phường 4, Quận 3, TP. HCM",
            "Gần Chợ Bàn Cờ, Hồ Con Rùa 1.5km", 3, 1, 2, 650000, 0, 1, 1, 0, 0,
            ["Cho thú cưng", "Thiên đường ăn vặt ẩm thực hẻm", "Bếp nấu ăn gia đình", "Không gian ấm cúng"],
            "Trải nghiệm đời sống hẻm Sài Gòn đích thực, xung quanh là hàng trăm món ăn đường phố nức tiếng của chợ Bàn Cờ."
        ),
        (
            "EkkoStay The River - Penthouse View Sông Đỉnh Cao", "Quận 2", "Khu Đô Thị Thủ Thiêm, An Khánh, TP. Thủ Đức, TP. HCM",
            "Chân Cầu Ba Son, đối diện bến Bạch Đằng Quận 1", 8, 4, 4, 4500000, 1, 0, 1, 1, 1,
            ["Bồn tắm kính view panorama Quận 1", "Hồ bơi riêng tầng cao", "Bếp đảo chuẩn 5 sao", "Sân tiệc BBQ rượu vang"],
            "Penthouse đẳng cấp nhất khu Thủ Thiêm với tầm nhìn triệu đô ôm trọn skyline Sài Gòn tráng lệ bên bờ sông."
        ),
        (
            "EkkoStay Hồ Con Rùa - Studio Nghệ Thuật", "Quận 3", "Trần Cao Vân, Phường 6, Quận 3, TP. HCM",
            "Cách Hồ Con Rùa 200m, Nhà Thờ Đức Bà 500m", 2, 1, 1, 750000, 1, 0, 0, 0, 0,
            ["Bồn tắm đứng & bồn ngâm", "Khu cà phê Hồ Con Rùa", "Nhiều cây cổ thụ râm mát", "Decor nghệ thuật"],
            "Khu vực thanh bình và rợp bóng cây xanh đẹp nhất trung tâm Sài Gòn, rất gần Nhà Thờ Đức Bà và Dinh Độc Lập."
        ),
        (
            "EkkoStay Airport Transit - Căn Hộ Gần Sân Bay", "Tân Bình", "Hồng Hà, Phường 2, Tân Bình, TP. HCM",
            "Cách Sân bay Tân Sơn Nhất 500m (5 phút di chuyển)", 3, 1, 2, 700000, 0, 1, 1, 1, 0,
            ["Hồ bơi toà nhà", "Cho thú cưng", "Đưa đón sân bay thuận tiện", "Máy giặt sấy trong phòng"],
            "Lựa chọn lý tưởng cho khách quá cảnh hoặc cần bay sớm, di chuyển ra sân bay Tân Sơn Nhất chỉ mất 5 phút."
        ),
        (
            "EkkoStay Masteri Thảo Điền - Căn Hộ Xanh", "Quận 2", "159 Xa Lộ Hà Nội, Thảo Điền, TP. Thủ Đức, TP. HCM",
            "Sát Ga Metro Thảo Điền, TTTM Vincom Mega Mall", 4, 2, 2, 1300000, 0, 1, 1, 1, 0,
            ["Cho thú cưng", "Hồ bơi lớn", "Kết nối trực tiếp ga Metro", "Sân tennis & bóng rổ"],
            "Căn hộ hiện đại đầy đủ tiện ích trong khu dân cư văn minh Thảo Điền, kết nối tuyến Metro đi thẳng vào Quận 1."
        ),
        (
            "EkkoStay Sunwah Pearl - Căn 1PN Siêu Sang", "Bình Thạnh", "90 Nguyễn Hữu Cảnh, Phường 22, Bình Thạnh, TP. HCM",
            "Cạnh Cầu Thủ Thiêm 1, cách Quận 1 3 phút", 2, 1, 1, 1500000, 1, 0, 1, 1, 0,
            ["Bồn tắm nằm cao cấp", "Hồ bơi tràn bờ view sông", "Ban công ngắm pháo hoa", "Bếp từ hiện đại"],
            "Tận hưởng không gian sống thượng lưu tại toà Sunwah Pearl cao cấp, ngắm sông Sài Gòn và trung tâm quận 1 rực rỡ ánh đèn."
        ),
        (
            "EkkoStay Chợ Lớn - Nét Đẹp Hoa Kiều", "Quận 5", "Nguyễn Trãi, Phường 11, Quận 5, TP. HCM",
            "Khu phố Tàu Chợ Lớn, gần Chùa Bà Thiên Hậu", 4, 2, 2, 800000, 0, 1, 1, 0, 0,
            ["Cho thú cưng", "Không gian văn hoá người Hoa", "Trà cung đình miễn phí", "Thiên đường ẩm thực dimsum"],
            "Khám phá nét kiến trúc và văn hoá người Hoa độc đáo tại Chợ Lớn, thưởng thức các món ăn trứ danh chỉ cách vài bước chân."
        ),
        (
            "EkkoStay Phan Xích Long - Phố Ẩm Thực Phú Nhuận", "Phú Nhuận", "Hoa Phượng, Phường 2, Phú Nhuận, TP. HCM",
            "Trung tâm phố ẩm thực Phan Xích Long", 2, 1, 1, 650000, 1, 1, 1, 0, 0,
            ["Bồn tắm nằm", "Cho thú cưng", "Bao quanh bởi hàng trăm quán ăn, trà sữa", "Giờ giấc tự do"],
            "Nằm giữa con đường ẩm thực sầm uất nhất Phú Nhuận, thuận tiện di chuyển cả về Quận 1 và sân bay trong 10 phút."
        ),
        (
            "EkkoStay Bình An - Nhà Phố Bên Bến Du Thuyền", "Quận 2", "Đường số 12, Phường Bình An, TP. Thủ Đức, TP. HCM",
            "Gần Bến Buýt Sông Bình An, Cầu Sài Gòn", 6, 3, 3, 2100000, 1, 1, 1, 0, 1,
            ["Bồn tắm thư giãn", "Cho thú cưng", "Sân nướng BBQ ven sông", "Trải nghiệm bến buýt sông Waterbus"],
            "Ngôi nhà thoáng mát với sân vườn tiệc nướng, chỉ cần đi bộ 3 phút ra bến Waterbus ngắm cảnh hoàng hôn trên sông Sài Gòn."
        )
    ]
    for item in hcm_templates:
        homestays.append(("TP. Hồ Chí Minh", *item))

    # -------------------------------------------------------------
    # 3. VŨNG TÀU (~16 CĂN)
    # -------------------------------------------------------------
    vungtau_templates = [
        (
            "EkkoStay Ocean View Bãi Trước - Căn Hộ Hoàng Hôn", "Phường 1", "04 Trần Phú, Phường 1, TP. Vũng Tàu",
            "Sát biển Bãi Trước, gần Cáp Treo Hồ Mây", 4, 2, 2, 1200000, 1, 1, 1, 1, 0,
            ["Bồn tắm view biển ngắm hoàng hôn", "Hồ bơi toà nhà", "Cho thú cưng", "Ban công panorama trực diện biển"],
            "Ngồi ngâm mình trong bồn tắm kính ngắm trọn hoàng hôn đỏ rực buông xuống biển Vũng Tàu, vị trí sát bờ biển Bãi Trước."
        ),
        (
            "EkkoStay Seaview Bãi Sau - 2 Phút Ra Bãi Tắm", "Phường Thắng Tam", "02 Lê Hồng Phong nối dài, Thắng Tam, TP. Vũng Tàu",
            "Quảng trường Cột Cờ Bãi Sau, cách bãi tắm 150m", 4, 2, 2, 1100000, 0, 1, 1, 1, 0,
            ["Cho mang thú cưng", "Đi bộ ra bãi tắm Bãi Sau 2 phút", "Hồ bơi toà nhà", "Bếp nấu hải sản đầy đủ gia vị"],
            "Bước chân xuống sảnh là bãi cát vàng Bãi Sau, rất thuận tiện tắm biển và ăn hải sản đêm tại chợ đêm Vũng Tàu."
        ),
        (
            "EkkoStay Palm Villa - Biệt Thự Hồ Bơi Bãi Dâu", "Phường 5", "125 Trần Phú, Phường 5, TP. Vũng Tàu",
            "Khu Bãi Dâu, gần chùa Thích Ca Phật Đài", 10, 4, 5, 3400000, 1, 1, 1, 1, 1,
            ["Hồ bơi riêng ngoài trời", "Bồn tắm nằm", "Sân nướng BBQ hải sản 80m2", "Cho thú cưng", "Dàn karaoke gia đình"],
            "Biệt thự lưng tựa núi mặt hướng biển Bãi Dâu thanh bình, hồ bơi riêng tư tuyệt đối cùng sân BBQ nướng hải sản cực đã."
        ),
        (
            "EkkoStay Lighthouse Loft - Đồi Hải Đăng", "Phường 2", "22 Hải Đăng, Phường 2, TP. Vũng Tàu",
            "Đường lên ngọn Hải Đăng, gần quán Yaourt Cô Tiên", 2, 1, 1, 650000, 1, 1, 0, 0, 1,
            ["Bồn tắm gỗ ngoài trời", "Cho thú cưng", "View ôm trọn thành phố biển", "Không khí mát mẻ trên núi"],
            "Căn loft nhỏ yên tĩnh trên sườn núi nhỏ, đường đi bộ lên ngọn hải đăng Vũng Tàu, gió núi lồng lộng mát mẻ cả ngày."
        ),
        (
            "EkkoStay Nghinh Phong - Studio Mũi Nghinh Phong", "Phường 2", "01 Hạ Long, Phường 2, TP. Vũng Tàu",
            "Sát Mũi Nghinh Phong, Cổng Trời, Tượng Chúa Kito", 2, 1, 1, 750000, 1, 0, 1, 0, 0,
            ["Bồn tắm kính view biển", "Đi bộ 3 phút ra Cổng Trời", "Ngắm bình minh và hoàng hôn", "Bếp nấu ăn"],
            "Tọa lạc tại địa danh ngắm gió nổi tiếng nhất Vũng Tàu, căn phòng ngập tràn hương vị biển mặn mòi và tầm nhìn bao la."
        ),
        (
            "EkkoStay Melody Bãi Sau - Căn Hộ Chung Cư", "Phường Thắng Tam", "149 Võ Thị Sáu, Thắng Tam, TP. Vũng Tàu",
            "Gần ngã tư Hoàng Hoa Thám - Võ Thị Sáu, cách biển 400m", 6, 2, 3, 1000000, 0, 1, 1, 0, 0,
            ["Cho thú cưng", "Bếp gia đình rộng rãi", "Gần chợ xóm Lưới mua hải sản", "Máy giặt sấy"],
            "Căn hộ tiện nghi cho gia đình 5-6 người, gần chợ hải sản Xóm Lưới tươi sống mua về tự chế biến tại bếp."
        ),
        (
            "EkkoStay Thủy Tiên - Căn Hộ Sát Bờ Cát Long Cung", "Phường 10", "Đường D5, Phường 10, TP. Vũng Tàu",
            "Bãi tắm Long Cung - Thuỷ Tiên", 4, 2, 2, 950000, 0, 1, 1, 0, 1,
            ["Cho thú cưng tự do", "Bãi biển riêng sạch sẽ, ít sóng lớn", "Khuôn viên nướng BBQ bờ biển", "Bãi đậu xe rộng"],
            "Khu vực biển Thuỷ Tiên sóng êm và cát mịn, bãi tắm riêng yên tĩnh không chen chúc như trung tâm."
        ),
        (
            "EkkoStay White Palace - Villa Trắng Sang Trọng", "Phường 8", "36 Chu Mạnh Trinh, Phường 8, TP. Vũng Tàu",
            "Cách Bãi Sau 800m", 12, 5, 6, 3800000, 1, 0, 1, 1, 1,
            ["Hồ bơi điện phân muối an toàn da em bé", "Bàn bida giải trí", "Bồn tắm Jacuzzi", "Sân tiệc nướng BBQ 20 người"],
            "Dinh thự tone trắng Địa Trung Hải siêu sang với bàn bida, hồ bơi nước mặn và không gian sinh hoạt chung rộng lớn."
        ),
        (
            "EkkoStay The Song - Căn Hộ Du Lịch 5 Sao", "Phường Thắng Tam", "28 Thi Sách, Thắng Tam, TP. Vũng Tàu",
            "Cạnh siêu thị Lotte Mart, cách Bãi Sau 300m", 4, 2, 2, 1350000, 1, 0, 1, 1, 0,
            ["Hồ bơi vô cực trên mây tầng 36", "Bồn tắm cao cấp", "Công viên nước trẻ em", "Phòng gym & Yoga"],
            "Trải nghiệm tiện ích resort 5 sao tại toà The Sóng nổi tiếng nhất Vũng Tàu với hồ bơi vô cực ngắm trọn bờ biển Bãi Sau."
        ),
        (
            "EkkoStay Sunset Trần Phú - Nhà Gỗ Ngắm Biển", "Phường 5", "88 Trần Phú, Phường 5, TP. Vũng Tàu",
            "Gần các nhà hàng hải sản Gành Hào, Lâm Đường", 2, 1, 1, 700000, 1, 1, 0, 0, 1,
            ["Bồn tắm lộ thiên sân sau", "Cho thú cưng", "Sát vách nhà hàng Gành Hào", "Ngắm hoàng hôn trên biển"],
            "Ngôi nhà gỗ ấm cúng nép sát vách đá bờ biển Trần Phú, nghe sóng vỗ rì rào và thưởng thức hải sản tươi ngon."
        ),
        (
            "EkkoStay Golden Beach - Nhà Phố Du Lịch", "Phường 2", "54 Phan Chu Trinh, Phường 2, TP. Vũng Tàu",
            "Gần Đồi Con Heo, Bãi Sau 500m", 8, 3, 4, 1800000, 0, 1, 1, 0, 1,
            ["Cho thú cưng", "Sân BBQ có mái che", "Bếp nấu gia đình", "Chỗ đậu ô tô trong nhà"],
            "Nhà phố nguyên căn 3 tầng độc lập, có gara ô tô và sân thượng tổ chức tiệc nướng hải sản ấm cúng."
        ),
        (
            "EkkoStay Bãi Dâu Chill - Căn Hộ Tầng Thấp", "Phường 5", "102 Trần Phú, Phường 5, TP. Vũng Tàu",
            "Bãi Dâu, gần Bạch Dinh", 2, 1, 1, 580000, 0, 1, 1, 0, 0,
            ["Cho mang thú cưng", "Không gian tĩnh lặng ngắm biển", "Bếp nhỏ xinh", "Giá sinh viên"],
            "Không gian yên ả không khói bụi xe cộ, thích hợp cho những ai muốn tìm một nơi đọc sách, nghe sóng biển vỗ."
        ),
        (
            "EkkoStay Hillside Villa - Biệt Thự Núi Nhỏ", "Phường 2", "Hẻm 44 Vi Ba, Phường 2, TP. Vũng Tàu",
            "Đường Núi Lớn - Vi Ba ngắm toàn cảnh Vũng Tàu", 10, 4, 5, 2900000, 1, 1, 1, 1, 1,
            ["Hồ bơi view núi và biển", "Bồn tắm lớn", "Sân BBQ trên cao", "Cho thú cưng", "Đường chạy bộ Núi Lớn"],
            "Toạ lạc trên cung đường chạy bộ Vi Ba nổi tiếng, khí hậu trong lành, ngắm trọn vẹn cả biển Đông và thành phố."
        ),
        (
            "EkkoStay Little Beach House - Nhà Nhỏ Sát Biển", "Phường 1", "18 Ba Cu, Phường 1, TP. Vũng Tàu",
            "Gần công viên Bãi Trước, Bảo tàng Vũng Tàu", 2, 1, 1, 620000, 1, 0, 0, 0, 0,
            ["Bồn tắm thư giãn", "Gần bến tàu cao tốc Cần Giờ", "Đi dạo công viên bờ biển Bãi Trước", "Nhiều quán ăn sáng"],
            "Ngôi nhà nhỏ xinh nằm ngay đầu đường Ba Cu trung tâm, thuận tiện đi dạo mát công viên Bãi Trước và bến tàu cánh ngầm."
        ),
        (
            "EkkoStay Oasky Seaview - Tầng Cao 30+", "Phường Thắng Tam", "02 Lê Hồng Phong, Thắng Tam, TP. Vũng Tàu",
            "Toà nhà Oasky Sơn Thịnh Bãi Sau", 6, 2, 3, 1300000, 1, 1, 1, 0, 0,
            ["Bồn tắm tròn view biển", "Cho thú cưng", "Tầng cao gió lộng", "Đi bộ ra biển 1 phút"],
            "Tầng cao ngắm toàn bộ vòng cung bờ biển Bãi Sau tuyệt mỹ, gió biển tự nhiên không cần bật điều hoà."
        ),
        (
            "EkkoStay Garden Pool Villa - Biệt Thự Khu Á Châu", "Phường 2", "Đường Hoàng Hoa Thám, Khu Á Châu, TP. Vũng Tàu",
            "Khu biệt thự Á Châu yên tĩnh, trung tâm Bãi Sau", 10, 4, 5, 3100000, 1, 1, 1, 1, 1,
            ["Hồ bơi xanh mát", "Bồn tắm thư giãn", "Sân cỏ BBQ rộng rãi", "Cho thú cưng", "Bàn bi lắc"],
            "Biệt thự sang trọng nằm trong khu đô thị Á Châu an ninh cao cấp, có hồ bơi riêng và sân nướng BBQ hải sản thoải mái."
        )
    ]
    for item in vungtau_templates:
        homestays.append(("Vũng Tàu", *item))

    return homestays

def seed_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. Đọc và thực thi lại schema.sql
    with open("schema.sql", "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # Dọn dẹp dữ liệu cũ
    cursor.execute("DELETE FROM bookings;")
    cursor.execute("DELETE FROM homestay_policies;")
    cursor.execute("DELETE FROM homestays;")

    # 2. Sinh và nạp 50 Homestays
    raw_homestays = generate_homestays()
    print(f"Tổng số homestays được tạo: {len(raw_homestays)} căn.")

    homestays_insert_data = []
    policies_insert_data = []

    for index, item in enumerate(raw_homestays, start=1):
        city, name, district, address, landmark, max_guests, bedrooms, beds, price, bathtub, pets, kitchen, pool, bbq, amenities, desc = item
        
        # Tọa độ cơ bản theo thành phố
        if city == "Đà Lạt":
            lat = 11.9404 + random.uniform(-0.03, 0.03)
            lng = 108.4583 + random.uniform(-0.03, 0.03)
        elif city == "TP. Hồ Chí Minh":
            lat = 10.7769 + random.uniform(-0.04, 0.04)
            lng = 106.7009 + random.uniform(-0.04, 0.04)
        else: # Vũng Tàu
            lat = 10.3460 + random.uniform(-0.03, 0.03)
            lng = 107.0843 + random.uniform(-0.03, 0.03)

        homestays_insert_data.append((
            index, name, city, district, address, landmark, round(lat, 6), round(lng, 6),
            max_guests, bedrooms, beds, price,
            bathtub, pets, kitchen, pool, bbq,
            json.dumps(amenities, ensure_ascii=False), desc, "ACTIVE"
        ))

        # Thêm các chính sách chuẩn chuỗi cho từng homestay (để RAG truy vấn theo homestay_id)
        for topic, title, content in COMMON_POLICIES:
            # Điều chỉnh riêng nội dung chính sách Thú cưng tuỳ căn
            if topic == "pets":
                if pets == 1:
                    custom_content = f"Căn {name} CHO PHÉP mang thú cưng (chó/mèo dưới 10kg). Phụ phí vệ sinh là 100.000 VNĐ/bé/đêm. Yêu cầu chủ mang tã/bỉm cho bé."
                else:
                    custom_content = f"Căn {name} TUYỆT ĐỐI KHÔNG NHẬN THÚ CƯNG nhằm đảm bảo tiêu chuẩn phòng sạch sẽ và không gian chung."
                policies_insert_data.append((index, topic, title, custom_content))
            elif topic == "bbq":
                if bbq == 1:
                    custom_content = f"Căn {name} CÓ SÂN VÀ BẾP NƯỚNG BBQ. Chuỗi hỗ trợ bếp nướng than với phí than và dọn rửa tro là 120.000 VNĐ/lần. Vui lòng dừng tiệc trước 22:30."
                else:
                    custom_content = f"Căn {name} KHÔNG CÓ BẾP BBQ ngoài trời để phòng chống cháy nổ."
                policies_insert_data.append((index, topic, title, custom_content))
            else:
                policies_insert_data.append((index, topic, title, content))

    # Nạp Homestays vào DB
    cursor.executemany("""
        INSERT INTO homestays (
            id, name, city, district, address, landmark, latitude, longitude,
            max_guests, num_bedrooms, num_beds, price_per_night,
            has_bathtub, allows_pets, has_kitchen, has_swimming_pool, has_bbq,
            amenities, description, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, homestays_insert_data)

    # Nạp Policies vào DB
    cursor.executemany("""
        INSERT INTO homestay_policies (homestay_id, topic, title, content)
        VALUES (?, ?, ?, ?);
    """, policies_insert_data)

    # 3. Nạp một vài đơn Booking mẫu để test trùng ngày
    sample_bookings = [
        ("HB-1001", 1, "Nguyễn Văn Hùng", "0901234567", "2026-11-10", "2026-11-12", 2, 1300000, "CONFIRMED"),
        ("HB-1002", 3, "Lê Thị Bích", "0912345678", "2026-11-15", "2026-11-18", 8, 7800000, "CONFIRMED"),
        ("HB-1003", 20, "Phạm Quốc Bảo", "0933445566", "2026-11-20", "2026-11-22", 4, 3600000, "CONFIRMED"),
        ("HB-1004", 36, "Đỗ Hoàng Long", "0988776655", "2026-11-12", "2026-11-14", 4, 2400000, "CONFIRMED")
    ]
    cursor.executemany("""
        INSERT INTO bookings (booking_code, homestay_id, customer_name, customer_phone, check_in, check_out, num_guests, total_price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, sample_bookings)

    conn.commit()
    conn.close()
    print("✅ Đã nạp thành công 50 homestays chuỗi EkkoStay và các chính sách vào homestay.db!")

if __name__ == "__main__":
    seed_database()
