import pypandoc

content = r"""# Bộ kịch bản đặt phòng Homestay

Tài liệu này tổng hợp các tình huống khách hàng có thể gặp **chỉ trong nghiệp vụ tìm kiếm và đặt phòng Homestay**. Phạm vi bắt đầu từ lúc khách tìm phòng, cung cấp tiêu chí, xem và chọn phòng, tạo booking, thanh toán, sửa đổi, hủy và kiểm tra trạng thái đặt phòng.

---

## 1. Tìm kiếm phòng theo nhu cầu

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Tìm phòng theo địa điểm | Tôi muốn tìm homestay ở Đà Lạt |
| 2 | Tìm theo khu vực | Có homestay ở gần trung tâm không? |
| 3 | Tìm theo địa chỉ | Tìm phòng tại khu vực X |
| 4 | Tìm theo số người | Tôi cần phòng cho 4 người |
| 5 | Tìm theo ngân sách | Tôi muốn thuê phòng dưới 1 triệu |
| 6 | Tìm theo thời gian | Tôi muốn đặt phòng cuối tuần này |
| 7 | Tìm theo số ngày | Tôi muốn thuê 3 ngày 2 đêm |
| 8 | Tìm theo loại phòng | Tôi muốn thuê nguyên căn |
| 9 | Tìm theo tiện ích | Có homestay nào có hồ bơi không? |
| 10 | Tìm theo nhiều điều kiện | Tìm villa cho 10 người, có hồ bơi, BBQ |
| 11 | Tìm phòng giá rẻ nhất | Có phòng nào rẻ nhất không? |
| 12 | Tìm phòng cao cấp | Tôi muốn thuê villa cao cấp |
| 13 | Tìm phòng còn trống | Ngày 15/11 còn phòng không? |

## 2. Kịch bản về số lượng khách

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Một người | Có phòng cho 1 người không? |
| 2 | Hai người | Tôi cần phòng cho 2 người |
| 3 | Nhóm nhỏ | Có phòng cho 4 người không? |
| 4 | Nhóm đông | Có villa cho 20 người không? |
| 5 | Gia đình | 2 người lớn và 2 trẻ em |
| 6 | Có trẻ sơ sinh | Nhà có nhận khách có em bé không? |
| 7 | Số người chưa chính xác | Khoảng 8–10 người |
| 8 | Tăng số người | Tôi muốn thêm 2 người |
| 9 | Giảm số người | Nhóm tôi giảm từ 10 còn 8 người |
| 10 | Vượt sức chứa | Nhà tối đa 10 người, tôi ở 12 được không? |
| 11 | Số người ngủ riêng | Có thể bố trí 6 giường riêng không? |
| 13 | Đặt nhiều căn | Có 2 căn gần nhau cho 20 người không? |
| 15 | Khách phát sinh | Có thể thêm khách sau khi đặt không? |

## 3. Kịch bản về ngân sách và giá phòng

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Ngân sách tối đa | Tôi có tối đa 3 triệu |
| 2 | Ngân sách mỗi đêm | Dưới 1 triệu/đêm |
| 3 | Ngân sách tổng chuyến đi | Tổng tiền không quá 5 triệu |
| 4 | Ngân sách mỗi người | Khoảng 500k/người |
| 5 | Ngân sách khoảng | Từ 2–3 triệu |
| 6 | Tìm giá thấp nhất | Phòng nào rẻ nhất? |
| 7 | Hỏi giá ngày thường | Ngày thường giá bao nhiêu? |
| 8 | Hỏi giá cuối tuần | Thứ 7 giá thế nào? |
| 9 | Hỏi giá ngày lễ | Dịp Tết giá bao nhiêu? |
| 10 | Hỏi giá theo mùa | Mùa cao điểm giá có tăng không? |
| 11 | Hỏi phụ thu | Thêm người có mất phí không? |
| 12 | Hỏi phí vệ sinh | Giá đã bao gồm phí vệ sinh chưa? |
| 13 | Hỏi phí dịch vụ | Có phụ thu gì không? |
| 14 | Yêu cầu giảm giá | Ở 5 đêm có được giảm giá không? |
| 15 | So sánh giá | Phòng A và B phòng nào rẻ hơn? |
| 16 | Thay đổi ngân sách | Tôi tăng ngân sách lên 4 triệu |
| 17 | Giảm ngân sách | Tìm phòng rẻ hơn, dưới 2 triệu |
| 18 | Giá không phù hợp | Có phòng nào rẻ hơn không? |

## 4. Kịch bản về ngày nhận và trả phòng

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Ngày check-in cụ thể | Tôi nhận phòng ngày 15/11 |
| 2 | Ngày check-out cụ thể | Tôi trả phòng ngày 17/11 |
| 3 | Ngày đi và ngày về | Tôi đi từ 15/11 đến 18/11 |
| 4 | Số ngày lưu trú | Tôi ở 3 ngày |
| 5 | Số đêm lưu trú | Tôi ở 2 đêm |
| 6 | Cuối tuần | Tôi muốn đặt thứ 7 và chủ nhật |
| 7 | Ngày lễ | Tôi muốn đặt dịp Tết |
| 8 | Ngày linh hoạt | Khoảng ngày 15–20 tháng sau |
| 9 | Chưa xác định ngày | Tôi chưa biết chính xác ngày đi |
| 10 | Đổi ngày check-in | Đổi ngày nhận phòng sang 20/11 |
| 11 | Đổi ngày check-out | Tôi muốn trả phòng muộn hơn 1 ngày |
| 12 | Kéo dài lưu trú | Tôi muốn ở thêm 2 đêm |
| 13 | Rút ngắn lưu trú | Tôi muốn trả phòng sớm hơn |
| 14 | Check-in sớm | Có thể nhận phòng lúc 8 giờ không? |
| 15 | Check-in muộn | Tôi đến lúc 23 giờ |
| 16 | Check-out muộn | Tôi muốn trả phòng lúc 15 giờ |
| 17 | Đặt phòng trong ngày | Hôm nay còn phòng không? |
| 18 | Đặt trước dài hạn | Tôi muốn đặt phòng trước 6 tháng |
| 19 | Đặt nhiều khoảng ngày | Tôi muốn đặt 2 đợt lưu trú khác nhau |
| 20 | Đặt ngày không liên tục | Tôi muốn ở ngày 15–16 và 20–21 |

## 5. Kịch bản về loại phòng và tiện ích

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Thuê nguyên căn | Tôi muốn thuê nguyên căn |
| 2 | Thuê phòng riêng | Tôi cần phòng riêng |
| 3 | Thuê villa | Có villa cho 15 người không? |
| 4 | Thuê bungalow | Có bungalow không? |
| 5 | Thuê căn hộ | Có căn hộ cho 4 người không? |
| 6 | Phòng nhiều giường | Có phòng 3 giường không? |
| 7 | Phòng nhiều phòng ngủ | Có villa 4 phòng ngủ không? |
| 8 | Hồ bơi | Tôi muốn có hồ bơi riêng |
| 9 | BBQ | Có khu vực BBQ không? |
| 10 | Karaoke | Có phòng karaoke không? |
| 11 | Bếp | Có bếp nấu ăn không? |
| 12 | View | Có phòng view núi không? |
| 13 | Ban công | Có phòng ban công không? |
| 14 | Bồn tắm | Có bồn tắm không? |
| 15 | Bãi đỗ xe | Có chỗ đậu ô tô không? |
| 16 | Thú cưng | Có cho mang chó theo không? |
| 17 | Nhiều tiện ích | Có hồ bơi, BBQ và karaoke không? |
| 18 | Thay đổi tiện ích | Không cần hồ bơi nữa, tìm phòng khác |
| 19 | Tiện ích bắt buộc | Bắt buộc phải có hồ bơi riêng |
| 20 | Tiện ích ưu tiên | Có hồ bơi thì tốt, không có cũng được |

## 6. Kịch bản kiểm tra tình trạng phòng trống

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Kiểm tra phòng theo ngày | Ngày 15/11 còn phòng không? |
| 2 | Kiểm tra nhiều ngày | Từ 15 đến 18/11 còn phòng không? |
| 3 | Kiểm tra theo số người | Có phòng cho 10 người không? |
| 4 | Kiểm tra theo loại phòng | Villa còn trống không? |
| 5 | Kiểm tra theo tiện ích | Villa có hồ bơi còn trống không? |
| 6 | Kiểm tra số lượng phòng | Còn 3 phòng cùng lúc không? |
| 7 | Kiểm tra nhiều homestay | Có những homestay nào còn phòng? |
| 8 | Kiểm tra ngày thay thế | Nếu ngày 15 hết phòng thì ngày 16 còn không? |
| 9 | Hỏi phòng vừa hết | Phòng này vừa có người đặt à? |
| 10 | Hỏi thời gian cập nhật | Tình trạng phòng được cập nhật khi nào? |
| 11 | Phòng đang chờ xác nhận | Phòng này có người giữ chưa? |
| 12 | Giữ phòng | Có thể giữ phòng cho tôi không? |
| 13 | Chờ phòng trống | Nếu có người hủy thì báo tôi |
| 14 | Hết phòng | Có phòng nào tương tự không? |
| 15 | Kiểm tra lại | Kiểm tra lại phòng này giúp tôi |

## 7. Kịch bản so sánh và chọn phòng

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | So sánh hai phòng | So sánh phòng A và B |
| 2 | So sánh giá | Phòng nào rẻ hơn? |
| 3 | So sánh sức chứa | Phòng nào chứa được nhiều người hơn? |
| 4 | So sánh tiện ích | Phòng nào có nhiều tiện ích hơn? |
| 5 | So sánh diện tích | Phòng nào rộng hơn? |
| 6 | So sánh số phòng ngủ | Villa nào có nhiều phòng ngủ hơn? |
| 7 | So sánh tổng tiền | Ở 3 đêm thì chỗ nào rẻ hơn? |
| 8 | Chọn phòng tốt nhất | Theo bạn nên chọn phòng nào? |
| 9 | Chọn phòng rẻ nhất | Tôi chọn phòng rẻ nhất |
| 10 | Chọn phòng cao cấp | Tôi chọn phòng tốt nhất |
| 11 | Chọn theo ưu tiên | Tôi ưu tiên hồ bơi hơn giá |
| 12 | Thay đổi lựa chọn | Tôi không muốn phòng A nữa, chọn B |
| 13 | Xem chi tiết trước khi đặt | Cho tôi xem thông tin chi tiết phòng này |
| 14 | Chọn nhiều phòng | Tôi muốn chọn cả phòng A và B |

## 8. Kịch bản tạo đặt phòng

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Muốn đặt phòng | Tôi muốn đặt phòng này |
| 2 | Đặt nhanh | Đặt giúp tôi ngay |
| 3 | Đặt theo mã phòng | Tôi muốn đặt phòng HS001 |
| 4 | Đặt nguyên căn | Tôi muốn thuê nguyên căn này |
| 5 | Đặt nhiều phòng | Tôi muốn đặt 3 phòng |
| 6 | Đặt nhiều căn | Tôi muốn đặt 2 villa |
| 7 | Đặt hộ | Tôi đặt phòng cho bạn tôi |
| 8 | Đặt nhưng thiếu thông tin | Tôi muốn đặt nhưng chưa biết cần cung cấp gì |
| 9 | Kiểm tra lại thông tin | Xác nhận lại booking giúp tôi |
| 10 | Xác nhận đặt phòng | Tôi đồng ý đặt phòng |
| 11 | Chưa muốn đặt | Tôi chỉ muốn tham khảo trước |
| 12 | Muốn giữ phòng trước | Tôi muốn giữ phòng nhưng thanh toán sau |
| 13 | Đặt phòng chưa hoàn tất | Tôi đã bắt đầu đặt nhưng chưa xong |
| 14 | Đặt trùng | Tôi vô tình tạo hai booking |
| 15 | Đặt thành công | Booking của tôi đã được xác nhận chưa? |

## 9. Kịch bản thu thập thông tin người đặt

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Cung cấp tên | Tôi tên Nguyễn Văn A |
| 2 | Cung cấp số điện thoại | Số điện thoại của tôi là... |
| 3 | Cung cấp email | Email của tôi là... |
| 4 | Thay đổi tên | Tôi nhập sai tên |
| 5 | Thay đổi số điện thoại | Tôi muốn đổi số liên hệ |
| 6 | Thay đổi email | Tôi nhập sai email |
| 7 | Đặt hộ người khác | Người ở là bạn tôi, không phải tôi |
| 8 | Nhiều người đại diện | Tôi muốn thêm người liên hệ thứ hai |
| 9 | Thiếu thông tin | Tôi chưa muốn cung cấp email |
| 10 | Xác nhận thông tin | Kiểm tra lại thông tin người đặt |

## 10. Kịch bản đặt cọc và thanh toán

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Hỏi tiền cọc | Cần đặt cọc bao nhiêu? |
| 2 | Hỏi tỷ lệ cọc | Phải cọc 30% hay 50%? |
| 3 | Thanh toán toàn bộ | Tôi muốn thanh toán hết |
| 4 | Thanh toán một phần | Tôi muốn thanh toán trước một nửa |
| 5 | Chuyển khoản | Cho tôi thông tin chuyển khoản |
| 6 | Thanh toán QR | Có mã QR không? |
| 7 | Thanh toán tiền mặt | Có thể trả tiền mặt không? |
| 8 | Thanh toán thẻ | Có hỗ trợ thẻ ngân hàng không? |
| 9 | Xác nhận đã chuyển khoản | Tôi chuyển tiền rồi |
| 10 | Thanh toán thất bại | Tôi không thanh toán được |
| 11 | Chuyển thiếu | Tôi chuyển thiếu tiền |
| 12 | Chuyển thừa | Tôi chuyển dư tiền |
| 13 | Chưa thanh toán | Tôi đặt rồi, giờ thanh toán thế nào? |
| 14 | Thanh toán nhiều lần | Có thể chia thành 2 lần thanh toán không? |
| 15 | Kiểm tra công nợ | Tôi còn phải trả bao nhiêu? |
| 16 | Hỏi thời hạn thanh toán | Khi nào phải thanh toán tiền còn lại? |
| 17 | Xác nhận giao dịch | Kiểm tra giao dịch giúp tôi |
| 18 | Yêu cầu hóa đơn | Tôi muốn lấy hóa đơn VAT |

## 11. Kịch bản sửa đổi booking

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Đổi ngày check-in | Tôi muốn đổi ngày đến |
| 2 | Đổi ngày check-out | Tôi muốn đổi ngày về |
| 3 | Đổi cả hai ngày | Tôi muốn đổi lịch lưu trú |
| 4 | Tăng số người | Thêm 3 người vào booking |
| 5 | Giảm số người | Giảm từ 8 còn 5 người |
| 6 | Thêm phòng | Tôi muốn thêm một phòng |
| 7 | Bớt phòng | Tôi muốn hủy bớt một phòng |
| 8 | Đổi loại phòng | Đổi sang villa lớn hơn |
| 9 | Nâng cấp phòng | Tôi muốn nâng cấp lên phòng cao cấp |
| 10 | Hạ cấp phòng | Tôi muốn đổi sang phòng rẻ hơn |
| 11 | Thêm tiện ích | Tôi muốn thêm dịch vụ BBQ |
| 12 | Bỏ tiện ích | Tôi không cần dịch vụ BBQ nữa |
| 13 | Đổi người đặt | Tôi muốn thay đổi người đặt phòng |
| 14 | Đổi liên hệ | Tôi muốn đổi số điện thoại |
| 15 | Kiểm tra phí thay đổi | Đổi ngày có mất phí không? |
| 16 | Xác nhận thay đổi | Xác nhận lại thông tin sau khi sửa |

## 12. Kịch bản hủy phòng và hoàn tiền

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Hủy booking | Tôi muốn hủy phòng |
| 2 | Hủy một phòng | Tôi muốn hủy 1 trong 3 phòng |
| 3 | Hủy nhiều phòng | Tôi muốn hủy 2 phòng |
| 4 | Hủy toàn bộ | Tôi muốn hủy toàn bộ booking |
| 5 | Hỏi chính sách hủy | Hủy phòng có mất cọc không? |
| 6 | Hỏi phí hủy | Hủy phòng mất bao nhiêu tiền? |
| 7 | Hỏi hoàn cọc | Tôi có được hoàn tiền cọc không? |
| 8 | Hỏi thời gian hoàn tiền | Bao lâu nhận được tiền hoàn? |
| 9 | Kiểm tra trạng thái hoàn | Tiền hoàn đã được xử lý chưa? |
| 10 | Hủy nhầm | Tôi vừa hủy nhầm phòng |
| 11 | Muốn khôi phục booking | Có thể khôi phục booking không? |
| 12 | Hủy do hết nhu cầu | Tôi không muốn đi nữa |
| 13 | Hủy do thay đổi lịch | Tôi bận việc nên không thể đi |
| 14 | Hủy do thay đổi giá | Tôi không đồng ý mức giá mới |
| 15 | Hủy sau khi thanh toán | Tôi đã thanh toán toàn bộ, giờ muốn hủy |

## 13. Tình huống đặc biệt và ngoại lệ trong booking

| STT | Trường hợp | Ví dụ khách hàng |
|---|---|---|
| 1 | Khách đổi nhiều điều kiện liên tục | Đổi ngày, đổi người, đổi ngân sách |
| 2 | Khách cung cấp thông tin mâu thuẫn | 10 người nhưng chỉ muốn phòng 4 người |
| 3 | Khách không cung cấp ngày | Tôi muốn tìm phòng nhưng chưa biết ngày |
| 4 | Khách không cung cấp số người | Tìm giúp tôi một căn phù hợp |
| 5 | Khách không có ngân sách | Tìm phòng phù hợp nhất |
| 6 | Khách yêu cầu không thể đáp ứng | Villa 20 người nhưng chỉ có 2 phòng ngủ |
| 7 | Không có phòng đáp ứng đủ tiêu chí | Có hồ bơi và BBQ nhưng không có phòng phù hợp |
| 8 | Giá thay đổi khi đặt | Giá lúc tìm kiếm khác giá lúc đặt |
| 9 | Phòng bị người khác đặt trước | Tôi đang đặt thì phòng hết |
| 10 | Hai khách đặt cùng lúc | Phòng vừa được khách khác xác nhận |
| 11 | Booking chưa được xác nhận | Tôi đã đặt nhưng trạng thái vẫn pending |
| 12 | Booking hết hạn giữ chỗ | Tôi chưa thanh toán kịp |
| 13 | Khách muốn đặt lại | Tôi muốn đặt lại booking cũ |
| 14 | Khách muốn tiếp tục booking dang dở | Tiếp tục đặt phòng lúc nãy |
| 15 | Khách muốn kiểm tra booking | Kiểm tra đơn đặt phòng của tôi |
| 16 | Khách gửi nhiều yêu cầu trong một tin nhắn | 10 người, 2 đêm, hồ bơi, dưới 5 triệu |
| 17 | Khách thay đổi ý định | Không đặt phòng này nữa |
| 18 | Khách xác nhận nhầm | Tôi chưa đồng ý đặt, chỉ hỏi thôi |
| 19 | Khách muốn đặt nhưng phòng chưa xác nhận | Có thể gửi yêu cầu đặt trước không? |
| 20 | Khách muốn nhân viên xử lý | Cho tôi gặp nhân viên đặt phòng |

---

## 14. Tổng hợp Intent dành riêng cho Booking

| Intent | Chức năng |
|---|---|
| `SEARCH_ROOM` | Tìm kiếm phòng |
| `FILTER_ROOM` | Lọc phòng theo điều kiện |
| `CHECK_AVAILABILITY` | Kiểm tra phòng trống |
| `GET_ROOM_PRICE` | Hỏi giá và phụ phí |
| `GET_ROOM_DETAIL` | Xem thông tin phòng |
| `COMPARE_ROOM` | So sánh phòng |
| `SELECT_ROOM` | Chọn phòng |
| `CREATE_BOOKING` | Tạo booking |
| `UPDATE_BOOKING` | Sửa booking |
| `PAYMENT_BOOKING` | Thanh toán booking |
| `CANCEL_BOOKING` | Hủy booking |
| `CHECK_BOOKING` | Kiểm tra trạng thái booking |

### Ví dụ phân tích một câu khách hàng

> Tôi muốn tìm villa ở Đà Lạt cho 10 người, ngày 15/11 đến 17/11, có hồ bơi riêng, ngân sách tối đa 5 triệu. Nếu có phòng thì đặt giúp tôi.

AI cần nhận diện:

- `SEARCH_ROOM`
- `CHECK_AVAILABILITY`
- `CREATE_BOOKING` — ghi nhận ý định đặt, nhưng chưa tự động xác nhận booking.
- Entity: địa điểm, số người, ngày check-in, ngày check-out, tiện ích, ngân sách.

### Nguyên tắc xử lý

Chia rõ quy trình:

1. Tìm kiếm phòng.
2. Chọn phòng.
3. Kiểm tra tình trạng phòng và giá thực tế.
4. Xác nhận thông tin đặt phòng.
5. Tạo booking.
6. Thanh toán hoặc đặt cọc.
7. Xác nhận booking.

Không tự ý tạo hoặc xác nhận booking khi khách mới chỉ đang tham khảo hoặc chưa đồng ý với thông tin cuối cùng.
"""

output_path = "/mnt/data/bo-kich-ban-dat-phong-homestay.md"
pypandoc.convert_text(content, "md", format="md", outputfile=output_path, extra_args=["--standalone"])
print(f"Đã tạo file: {output_path}")
