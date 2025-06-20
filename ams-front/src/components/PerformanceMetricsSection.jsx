import AccessTimeIcon from "@mui/icons-material/AccessTime";
import { Box, Card, Stack, Typography } from "@mui/material";
import React from "react";

export function PerformanceMetricsSection() {
	return (
		<Box 
			className="overlap-wrapper"
			sx={{ 
				width: "410px", 
				height: "351px" 
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
					여유 기기 변동 추이
				</Typography>

				<Box
					className="description"
					sx={{
						position: "absolute",
						top: "251px",
						left: "23px",
						fontFamily: "Roboto, Helvetica",
						fontSize: "14px",
						letterSpacing: 0,
						lineHeight: "19.6px",
						whiteSpace: "nowrap",
					}}
				>
					<Box
						component="span"
						className="span"
						sx={{
							color: "var(--lineargrey)",
							fontWeight: 400,
						}}
					>
						(
					</Box>
					<Box
						component="span"
						className="text-wrapper-5"
						sx={{
							color: "var(--lineargreen)",
							fontWeight: 700,
						}}
					>
						+15%
					</Box>
					<Box
						component="span"
						className="span"
						sx={{
							color: "var(--lineargrey)",
							fontWeight: 400,
						}}
					>
						) 전월 대비 증가
					</Box>
				</Box>

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
					4분 전 업데이트
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
					className="bg-graph-2"
					sx={{
						position: "absolute",
						width: "378px",
						height: "202px",
						top: 0,
						left: "16px",
						borderRadius: "8px",
						boxShadow: "var(--drop-shadow-green)",
						background: "linear-gradient(180deg, rgba(99,185,103,1) 0%, rgba(75,166,79,1) 100%)",
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
						className="overlap-group-3"
						sx={{
							position: "relative",
							height: "116px",
						}}
					>
						<Box
							component="img"
							className="lines"
							src="https://c.animaapp.com/6S1yK5Ge/img/lines-1@2x.png"
							sx={{
								position: "absolute",
								width: "304px",
								height: "98px",
								top: "10px",
								left: "35px",
								objectFit: "cover",
							}}
						/>

						<Box
							component="img"
							className="group"
							src="https://c.animaapp.com/6S1yK5Ge/img/group-11-1@2x.png"
							sx={{
								position: "absolute",
								width: "322px",
								height: "88px",
								top: "20px",
								left: "29px",
								objectFit: "cover",
							}}
						/>

						<Box
							className="numbers-2"
							sx={{
								position: "absolute",
								height: "116px",
								top: 0,
								left: 0,
							}}
						>
							<Typography
								className="text-wrapper"
								sx={{
									position: "absolute",
									top: 0,
									left: 0,
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
								}}
							>
								150
							</Typography>

							<Typography
								className="text-wrapper-2"
								sx={{
									position: "absolute",
									top: "32px",
									left: 0,
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
								}}
							>
								100
							</Typography>

							<Typography
								className="element"
								sx={{
									position: "absolute",
									top: "64px",
									left: 0,
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
								}}
							>
								50
							</Typography>

							<Typography
								className="text-wrapper-6"
								sx={{
									position: "absolute",
									top: "96px",
									left: 0,
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
								}}
							>
								0
							</Typography>
						</Box>
					</Box>

					<Box
						className="navbar"
						sx={{
							position: "absolute",
							width: "350px",
							height: "20px",
							top: "121px",
							left: "6px",
							display: "flex",
							justifyContent: "space-between",
						}}
					>
						{["4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"].map((month, index) => (
							<Typography
								key={index}
								className={`text-wrapper-${index + 7}`}
								sx={{
									fontFamily: "Roboto, Helvetica",
									fontWeight: 400,
									color: "white",
									fontSize: "14px",
									opacity: 0.5,
								}}
							>
								{month}
							</Typography>
						))}
					</Box>
				</Box>
			</Box>
		</Box>
	);
}
