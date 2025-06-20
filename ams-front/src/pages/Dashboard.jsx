import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import BarChartIcon from "@mui/icons-material/BarChart";
import icon3dBox from "/icon-3d_box.svg";
import {Box, Typography} from "@mui/material";
import React from "react";
import {AnalyticsOverviewSection} from "../components/AnalyticsOverviewSection";
import {DataTableSection} from "../components/DataTableSection";
import {PerformanceMetricsSection} from "../components/PerformanceMetricsSection";
import {WebsiteViewsSection} from "../components/WebsiteViewsSection";

const Dashboard = () => {
	// Data for the stat cards
	const statCards = [
		{
			title: "총 자산",
			value: "281",
			change: "+10%",
			changeText: "전월 대비 증가",
			icon: <Box component="img" src={icon3dBox} sx={{width: 24, height: 24}}/>,
			iconBgColor: "#b8b8ff",
			positive: true,
		},
		{
			title: "신규 등록",
			value: "21",
			change: "+5%",
			changeText: "전주 대비",
			icon: <BarChartIcon/>,
			iconBgColor:
				"linear-gradient(180deg,rgba(233,59,119,1) 0%,rgba(218,31,99,1) 100%)",
			positive: true,
		},
		{
			title: "사용자",
			value: "85",
			changeText: "업데이트됨",
			icon: <AccountCircleIcon/>,
			iconBgColor:
				"linear-gradient(180deg,rgba(67,157,238,1) 0%,rgba(30,120,233,1) 100%)",
			noChange: true,
		},
	];

	return (
		<>
			{/* Stat Cards */}
			<Box
				sx={{
					display: 'flex',
					flexWrap: 'wrap',
					position: "relative",
					justifyContent: "space-between",
					marginBottom: "30px"
				}}
			>
				{statCards.map((card, index) => {
					const cardClass = index === 0 ? "card-report" :
						index === 1 ? "div-wrapper" : "card-report-2";

					return (
						<Box
							key={index}
							className={cardClass}
							sx={{
								position: "relative",
								width: {xs: '100%', sm: '332px'},
								maxWidth: '332px',
								height: "134px",
							}}
						>
							<Box
								sx={{
									position: "relative",
									height: "134px",
								}}
							>
								<Box
									sx={{
										width: "100%",
										height: "134px",
										position: "absolute",
										top: 0,
										left: 0,
										borderRadius: "8px",
										backgroundColor: "var(--linearwhite)",
										boxShadow: "var(--drop-shadow-black)",
									}}
								/>

								<Box
									sx={{
										width: "64px",
										height: "64px",
										position: "absolute",
										top: "-18px",
										left: "16px",
										borderRadius: "8px",
										background: card.iconBgColor,
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										color: "white",
										zIndex: 1,
									}}
								>
									{card.icon}
								</Box>

								<Typography
									sx={{
										position: "absolute",
										top: "16px",
										right: "16px",
										fontFamily: "Roboto, Helvetica",
										fontWeight: 300,
										color: "var(--lineargrey)",
										fontSize: "14px",
										letterSpacing: 0,
										lineHeight: "19.6px",
									}}
								>
									{card.title}
								</Typography>

								<Typography
									sx={{
										position: "absolute",
										top: "40px",
										right: "16px",
										fontFamily: "Roboto, Helvetica",
										fontWeight: 700,
										color: "var(--lineardark-blue)",
										fontSize: "18px",
										letterSpacing: 0,
										lineHeight: "25.2px",
									}}
								>
									{card.value}
								</Typography>

								<Box
									component="img"
									src="https://c.animaapp.com/6S1yK5Ge/img/line-6.svg"
									sx={{
										position: "absolute",
										width: "90%",
										height: "1px",
										top: "92px",
										left: "16px",
									}}
								/>

								{!card.noChange ? (
									<Typography
										sx={{
											position: "absolute",
											top: "104px",
											left: "16px",
											fontFamily: "Roboto, Helvetica",
											fontSize: "14px",
											letterSpacing: 0,
											lineHeight: "19.6px",
										}}
									>
										<Box
											component="span"
											sx={{
												fontWeight: 700,
												color: card.positive ? "var(--lineargreen)" : "var(--linearred)",
											}}
										>
											{card.change}
										</Box>{" "}
										<Box
											component="span"
											sx={{
												fontWeight: 300,
												color: "var(--lineargrey)",
											}}
										>
											{card.changeText}
										</Box>
									</Typography>
								) : (
									<Typography
										sx={{
											position: "absolute",
											top: "104px",
											left: "16px",
											fontFamily: "Roboto, Helvetica",
											fontWeight: 300,
											color: "var(--lineargrey)",
											fontSize: "14px",
											letterSpacing: 0,
											lineHeight: "19.6px",
										}}
									>
										{card.changeText}
									</Typography>
								)}
							</Box>
						</Box>
					);
				})}
			</Box>

			{/* Chart Sections */}
			<Box
				sx={{
					display: 'flex',
					flexDirection: {xs: 'column', lg: 'row'},
					flexWrap: 'wrap',
					gap: '20px',
					position: "relative",
					justifyContent: "space-between",
					marginBottom: "30px"
				}}
			>
				<Box
					sx={{
						position: "relative",
						width: {xs: '100%', sm: '410px'},
						maxWidth: '410px',
					}}
				>
					<WebsiteViewsSection/>
				</Box>

				<Box
					sx={{
						position: "relative",
						width: {xs: '100%', sm: '410px'},
						maxWidth: '410px',
					}}
				>
					<PerformanceMetricsSection/>
				</Box>

				<Box
					sx={{
						position: "relative",
						width: {xs: '100%', sm: '410px'},
						maxWidth: '410px',
					}}
				>
					<AnalyticsOverviewSection/>
				</Box>
			</Box>

			{/* Data Table */}
			<Box
				sx={{
					position: "relative",
					width: {xs: '100%', md: '1270px'},
					overflowX: 'hidden',
					marginBottom: "30px"
				}}
			>
				<DataTableSection/>
			</Box>
		</>
	);
};

export default Dashboard;
