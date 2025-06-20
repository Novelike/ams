import AccessTimeIcon from "@mui/icons-material/AccessTime";
import { Box, Card, Divider, Stack, Typography } from "@mui/material";
import React from "react";

export function WebsiteViewsSection() {
	return (
		<Box 
			className="card-website-views"
			sx={{ 
				width: "410px", 
				height: "351px",
			}}
		>
			<Box 
				className="overlap"
				sx={{ 
					position: "relative", 
					height: "351px" 
				}}
			>
				<Box
					className="rectangle"
					sx={{
						width: "410px",
						height: "327px",
						position: "absolute",
						top: "24px",
						left: 0,
						borderRadius: "8px",
						boxShadow: "var(--drop-shadow-black)",
						backgroundColor: "var(--linearwhite)",
					}}
				/>

				<Typography
					className="title"
					sx={{
						position: "absolute",
						top: "227px",
						left: "23px",
						fontFamily: "Roboto, Helvetica",
						fontWeight: 700,
						color: "var(--lineardark-blue)",
						fontSize: "16px",
						letterSpacing: 0,
						lineHeight: "22.4px",
						whiteSpace: "nowrap",
					}}
				>
					기기 종류별 총 대수
				</Typography>

				<Typography
					className="status"
					sx={{
						position: "absolute",
						top: "305px",
						left: "39px",
						fontFamily: "Roboto, Helvetica",
						fontWeight: 400,
						color: "var(--lineargrey)",
						fontSize: "14px",
						letterSpacing: 0,
						lineHeight: "19.6px",
						whiteSpace: "nowrap",
					}}
				>
					최근 업데이트: 오늘
				</Typography>

				<Box
					component="img"
					className="icon-clock"
					src="https://c.animaapp.com/6S1yK5Ge/img/icon-12px-clock-outline-2.svg"
					sx={{
						position: "absolute",
						width: "12px",
						height: "12px",
						top: "310px",
						left: "23px",
					}}
				/>

				<Box
					component="img"
					className="line"
					src="https://c.animaapp.com/6S1yK5Ge/img/line-2.svg"
					sx={{
						position: "absolute",
						width: "378px",
						height: "1px",
						top: "288px",
						left: "16px",
						objectFit: "cover",
					}}
				/>

				<Box
					className="bg-graph"
					sx={{
						position: "absolute",
						width: "378px",
						height: "202px",
						top: 0,
						left: "16px",
						borderRadius: "8px",
						boxShadow: "var(--drop-shadow-red)",
						background: "linear-gradient(180deg, rgba(233, 59, 119, 1) 0%, rgba(218, 31, 99, 1) 100%)",
					}}
				/>

				<Box
					className="div-2"
					sx={{
						position: "absolute",
						width: "354px",
						height: "142px",
						top: "30px",
						left: "28px",
					}}
				>
					<Box
						className="overlap-group"
						sx={{
							position: "relative",
							height: "142px",
						}}
					>
						{/* Y축 숫자 라벨들 */}
						<Box
							className="numbers"
							sx={{
								position: "absolute",
								width: "354px",
								height: "142px",
								top: 0,
								left: 0,
							}}
						>
							<Typography
								className="text-wrapper"
								sx={{
									position: "absolute",
									top: "8px",
									left: 0,
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									whiteSpace: "nowrap",
								}}
							>
								60
							</Typography>

							<Typography
								className="text-wrapper-2"
								sx={{
									position: "absolute",
									top: "41px",
									left: 0,
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									whiteSpace: "nowrap",
								}}
							>
								40
							</Typography>

							<Typography
								className="text-wrapper-3"
								sx={{
									position: "absolute",
									top: "74px",
									left: 0,
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									whiteSpace: "nowrap",
								}}
							>
								20
							</Typography>

							<Typography
								className="text-wrapper-4"
								sx={{
									position: "absolute",
									top: "107px",
									left: "8px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									whiteSpace: "nowrap",
								}}
							>
								0
							</Typography>

							{/* X축 라벨들 - 세로 그리드 라인과 정렬 */}
							<Typography
								className="m"
								sx={{
									position: "absolute",
									top: "122px",
									left: "45px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									textAlign: "center",
									transform: "translateX(-50%)",
									whiteSpace: "nowrap",
								}}
							>
								노트북
							</Typography>

							<Typography
								className="t"
								sx={{
									position: "absolute",
									top: "122px",
									left: "93px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									textAlign: "center",
									transform: "translateX(-50%)",
									whiteSpace: "nowrap",
								}}
							>
								키보드
							</Typography>

							<Typography
								className="w"
								sx={{
									position: "absolute",
									top: "122px",
									left: "141px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									textAlign: "center",
									transform: "translateX(-50%)",
									whiteSpace: "nowrap",
								}}
							>
								마우스
							</Typography>

							<Typography
								className="t-2"
								sx={{
									position: "absolute",
									top: "122px",
									left: "189px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									textAlign: "center",
									transform: "translateX(-50%)",
									whiteSpace: "nowrap",
								}}
							>
								패드
							</Typography>

							<Typography
								className="f"
								sx={{
									position: "absolute",
									top: "122px",
									left: "237px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									textAlign: "center",
									transform: "translateX(-50%)",
									whiteSpace: "nowrap",
								}}
							>
								가방
							</Typography>

							<Typography
								className="s"
								sx={{
									position: "absolute",
									top: "122px",
									left: "285px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									textAlign: "center",
									transform: "translateX(-50%)",
									whiteSpace: "nowrap",
								}}
							>
								데스크탑
							</Typography>

							<Typography
								className="s-2"
								sx={{
									position: "absolute",
									top: "122px",
									left: "333px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
									textAlign: "center",
									transform: "translateX(-50%)",
									whiteSpace: "nowrap",
								}}
							>
								모니터
							</Typography>
						</Box>

						<Box
							className="frame"
							sx={{
								position: "absolute",
								width: "329px",
								height: "99px",
								top: "11px",
								left: "25px",
							}}
						>
							{/* CSS 그리드 배경 - 정렬된 라인들 */}
							<Box
								className="background"
								sx={{
									position: "absolute",
									width: "329px",
									height: "99px",
									top: 0,
									left: 0,
									opacity: 0.5,
									// 외곽 테두리
									border: "1px dashed #FFFFFF",
									boxSizing: "border-box",
									// 가로 그리드 라인들 - 균등 간격
									"&::before": {
										content: '""',
										position: "absolute",
										left: "0px",
										top: "33px",
										width: "329px",
										height: "0px",
										borderTop: "1px dashed #FFFFFF",
									},
									"&::after": {
										content: '""',
										position: "absolute",
										left: "0px",
										top: "66px",
										width: "329px",
										height: "0px",
										borderTop: "1px dashed #FFFFFF",
									},
								}}
							>
								{/* 세로 그리드 라인들 - 균등 간격 (329/7 = 47px 간격) */}
								{[47, 94, 141, 188, 235, 282].map((left, index) => (
									<Box
										key={`grid-line-${index}`}
										sx={{
											position: "absolute",
											width: "0px",
											height: "99px",
											left: `${left}px`,
											top: "0px",
											borderLeft: "1px dashed #FFFFFF",
										}}
									/>
								))}
							</Box>

							<Box
								className="bars"
								sx={{
									position: "absolute",
									width: "329px",
									height: "99px",
									top: 0,
									left: 0,
									display: "flex",
									justifyContent: "space-between",
									alignItems: "flex-end",
									padding: "0 20px",
								}}
							>
								<Box
									className="bar"
									sx={{
										width: "6px",
										height: "67px",
										backgroundColor: "white",
										borderRadius: "3px",
									}}
								/>

								<Box
									className="bar-2"
									sx={{
										width: "6px",
										height: "84px",
										backgroundColor: "white",
										borderRadius: "3px",
									}}
								/>

								<Box
									className="bar-2"
									sx={{
										width: "6px",
										height: "84px",
										backgroundColor: "white",
										borderRadius: "3px",
									}}
								/>

								<Box
									className="bar-2"
									sx={{
										width: "6px",
										height: "84px",
										backgroundColor: "white",
										borderRadius: "3px",
									}}
								/>

								<Box
									className="bar"
									sx={{
										width: "6px",
										height: "67px",
										backgroundColor: "white",
										borderRadius: "3px",
									}}
								/>

								<Box
									className="bar-3"
									sx={{
										width: "6px",
										height: "34px",
										backgroundColor: "white",
										borderRadius: "3px",
									}}
								/>

								<Box
									className="bar-4"
									sx={{
										width: "6px",
										height: "82px",
										backgroundColor: "white",
										borderRadius: "3px",
									}}
								/>
							</Box>
						</Box>
					</Box>
				</Box>
			</Box>
		</Box>
	);
}
